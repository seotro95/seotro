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
