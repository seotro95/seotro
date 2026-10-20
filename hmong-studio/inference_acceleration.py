"""Remove an unused language-vocabulary projection from pinned Qwen2 decoding.

CosyVoice consumes Qwen2's final hidden states and applies its own speech-token
decoder.  Its legacy encoder calls Qwen2ForCausalLM anyway, so the original
language lm_head also runs and its logits are discarded.  This change executes
the same Qwen2 base model and KV cache directly; it does not quantize weights,
change sampling, shorten the script or change acoustic diffusion settings.
"""
from __future__ import annotations

import ast
import inspect
import textwrap
from types import MethodType


# Only this inspected legacy method is eligible.  A model-shaped object or a
# future encoder that transforms hidden states must keep its original behavior.
_LEGACY_STEP = """
def forward_one_step(self, xs, masks, cache=None):
    input_masks = masks[:, -1, :]
    outs = self.model(
        inputs_embeds=xs,
        attention_mask=input_masks,
        output_hidden_states=True,
        return_dict=True,
        use_cache=True,
        past_key_values=cache,
    )
    xs = outs.hidden_states[-1]
    new_cache = outs.past_key_values
    return xs, new_cache
"""
_LEGACY_AST = ast.dump(ast.parse(textwrap.dedent(_LEGACY_STEP)), include_attributes=False)


def _known_legacy_step(method):
    try:
        source = textwrap.dedent(inspect.getsource(method.__func__))
        return ast.dump(ast.parse(source), include_attributes=False) == _LEGACY_AST
    except (AttributeError, OSError, TypeError, SyntaxError, IndentationError):
        return False


def _forward_one_step_without_logits(self, xs, masks, cache=None):
    outs = self.model.model(
        inputs_embeds=xs,
        attention_mask=masks[:, -1, :],
        output_hidden_states=False,
        return_dict=True,
        use_cache=True,
        past_key_values=cache,
    )
    return outs.last_hidden_state, outs.past_key_values


def optimize_qwen_decode(backend):
    """Optimize a known Qwen2 encoder in memory; return whether it is active.

    Unknown backends, encoder implementations and model subclasses are left
    untouched.  Repeating this call on an optimized encoder is harmless.
    Model tensors and the verified on-disk snapshot are never modified.
    """
    try:
        from transformers.models.qwen2.modeling_qwen2 import Qwen2ForCausalLM, Qwen2Model
        encoder = backend.llm.llm
        model = encoder.model
        method = encoder.forward_one_step
        if (type(model) is not Qwen2ForCausalLM
                or type(model.model) is not Qwen2Model
                or getattr(method, '__self__', None) is not encoder):
            return False
        if getattr(method, '__func__', None) is _forward_one_step_without_logits:
            return True
        if not _known_legacy_step(method):
            return False
        encoder.forward_one_step = MethodType(_forward_one_step_without_logits, encoder)
        return True
    except (AttributeError, ImportError, ModuleNotFoundError):
        return False


def _cpu_text_embedding_on_input_device(self, indices):
    """Look up the unchanged CPU table, then restore the caller's device."""
    from torch.nn import Embedding
    return Embedding.forward(self, indices.to(self.weight.device)).to(indices.device)


def _low_vram_cuda(backend, torch):
    try:
        device = torch.device(backend.device)
        if device.type != 'cuda' or not torch.cuda.is_available():
            return False
        memory = torch.cuda.get_device_properties(device).total_memory
        return isinstance(memory, int) and not isinstance(memory, bool) and 0 < memory <= 8 * 1024 ** 3
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return False


def _move_text_table_to_cpu(backend, table):
    """Commit the storage/method change together, restoring both on failure."""
    original_data = table.weight.detach()
    original_forward = table.__dict__.get('forward')
    try:
        cpu_weight = original_data.to(device='cpu')
    except (RuntimeError, TypeError, ValueError):
        return False
    try:
        table.weight.data = cpu_weight
        table.forward = MethodType(_cpu_text_embedding_on_input_device, table)
    except (AttributeError, RuntimeError, TypeError, ValueError):
        try:
            table.weight.data = original_data
            if original_forward is None:
                if 'forward' in table.__dict__:
                    del table.forward
            else:
                table.forward = original_forward
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            raise RuntimeError('Không khôi phục được bảng chữ Qwen sau lỗi chuyển bộ nhớ. '
                               'Khởi động lại Studio trước khi tạo voice tiếp.') from exc
        return False
    # Status is optional. The byte count describes CUDA storage actually moved,
    # so forced CPU parity checks do not claim to have released any VRAM.
    try:
        backend._hmong_text_embedding_offloaded = True
        backend._hmong_text_embedding_bytes = (
            original_data.numel() * original_data.element_size()
            if original_data.device.type == 'cuda' else 0)
    except (AttributeError, TypeError):
        pass
    return True


def offload_qwen_text_embedding(backend, *, force=False):
    """Offload a verified tied Qwen text table on CUDA cards up to 8 GiB.

    The text table and unused language head share one Parameter. Moving only the
    unused head would therefore release no storage. The known optimized encoder
    accepts inputs_embeds, so only the text lookup needs the table: it can run on
    CPU once per utterance, returning the exact values to the input device. The
    speech embeddings and transformer keep their existing devices and dtypes.

    ``force=True`` permits the same path in CPU parity checks; it is not a user
    API option. Parameter identities, ties and state-dict keys are preserved.
    Unknown models and unsupported moves are left unchanged. No checkpoint is
    written. Native CUDA throughput still requires measurement on that GPU.
    """
    try:
        import torch
        from transformers.models.qwen2.modeling_qwen2 import Qwen2ForCausalLM, Qwen2Model
        if force is not True and not _low_vram_cuda(backend, torch):
            return False
        encoder = backend.llm.llm
        model = encoder.model
        method = encoder.forward_one_step
        if (type(model) is not Qwen2ForCausalLM
                or type(model.model) is not Qwen2Model
                or getattr(method, '__self__', None) is not encoder
                or getattr(method, '__func__', None) is not _forward_one_step_without_logits):
            return False
        table, head = model.model.embed_tokens, model.lm_head
        if (type(table) is not torch.nn.Embedding or type(head) is not torch.nn.Linear
                or table.weight is not head.weight or not model.config.tie_word_embeddings
                or table.training or head.training or model.training
                or table.weight.grad is not None or head.bias is not None
                or table.max_norm is not None or table.norm_type != 2.0
                or table.scale_grad_by_freq or table.sparse
                or table._forward_pre_hooks or table._forward_hooks or table._backward_hooks
                or table.num_embeddings != model.config.vocab_size
                or table.embedding_dim != model.config.hidden_size
                or head.in_features != table.embedding_dim
                or head.out_features != table.num_embeddings):
            return False
        forward = getattr(table.forward, '__func__', None)
        if forward is _cpu_text_embedding_on_input_device:
            return table.weight.device.type == 'cpu'
        if forward is not torch.nn.Embedding.forward:
            return False
    except (AttributeError, ImportError, ModuleNotFoundError, RuntimeError, TypeError, ValueError):
        return False
    # This changes shared storage rather than replacing the Parameter. Keep it
    # outside the guard's exception handler so a failed rollback remains fatal.
    return _move_text_table_to_cpu(backend, table)
