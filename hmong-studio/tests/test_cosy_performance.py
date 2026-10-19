"""Regression coverage for expensive conditioning and bounded long-form output."""
from pathlib import Path
from types import SimpleNamespace
import wave

import pytest

import cosy_engine as engine


@pytest.fixture(autouse=True)
def reference_cache(monkeypatch):
    from collections import OrderedDict
    monkeypatch.setattr(engine, '_reference_cache', OrderedDict())


class Frontend:
    device = 'cpu'

    def __init__(self):
        self.calls = []
        self.tokens = []
        self.acoustic = object()

    def _extract_text_token(self, text):
        self.tokens.append(text)
        return f'tokens:{text}', len(text)

    def frontend_instruct2(self, text, instruction, reference, rate, speaker):
        assert Path(reference).read_bytes() == b'decoded'
        assert rate == 24000 and speaker == ''
        self.calls.append((text, instruction))
        text_tokens, text_length = self._extract_text_token(text)
        prompt_tokens, prompt_length = self._extract_text_token(instruction)
        return {'text': text_tokens, 'text_len': text_length,
                'prompt_text': prompt_tokens, 'prompt_text_len': prompt_length,
                'flow_embedding': self.acoustic, 'prompt_speech_feat': self.acoustic}


@pytest.fixture
def decoded_reference(tmp_path, monkeypatch):
    source = tmp_path / 'reference.mp3'
    source.write_bytes(b'original-reference')
    decodes = []

    def decode(source, target):
        decodes.append(source)
        target.write_bytes(b'decoded')
    monkeypatch.setattr(engine, '_decode_reference', decode)
    return source, decodes


def test_reference_features_are_reused_but_text_and_style_are_fresh(decoded_reference):
    source, decodes = decoded_reference
    frontend = Frontend()
    first = engine._conditioned_inputs(frontend, 'Nyob zoo.', 'neutral', source, 24000, root='model')
    second = engine._conditioned_inputs(frontend, 'Kuv hais lus Hmoob.', 'review', source, 24000, root='model')
    assert len(decodes) == len(frontend.calls) == 1
    assert first['flow_embedding'] is second['flow_embedding'] is frontend.acoustic
    assert second['text'] == 'tokens:Kuv hais lus Hmoob.'
    assert second['prompt_text'] == 'tokens:review'
    # Mutating one request's dictionary must not corrupt the cached request.
    second.pop('flow_embedding')
    third = engine._conditioned_inputs(frontend, 'Zoo siab.', 'review', source, 24000, root='model')
    assert third['flow_embedding'] is frontend.acoustic
    assert len(decodes) == 1


def test_changed_reference_and_changed_model_invalidate_conditioning(decoded_reference):
    source, decodes = decoded_reference
    frontend = Frontend()
    engine._conditioned_inputs(frontend, 'a', 'neutral', source, 24000, root='first-model')
    source.write_bytes(b'a-different-reference')
    engine._conditioned_inputs(frontend, 'b', 'neutral', source, 24000, root='first-model')
    engine._conditioned_inputs(frontend, 'c', 'neutral', source, 24000, root='second-model')
    frontend.device = 'cuda'
    engine._conditioned_inputs(frontend, 'd', 'neutral', source, 24000, root='second-model')
    assert len(decodes) == len(frontend.calls) == 4


def test_conditioning_cache_is_bounded_and_evicts_least_recent_reference(tmp_path, decoded_reference):
    _, decodes = decoded_reference
    frontend = Frontend()
    references = []
    for index in range(engine._REFERENCE_CACHE_LIMIT + 1):
        source = tmp_path / f'{index}.wav'
        source.write_bytes(f'reference-{index}'.encode())
        references.append(source)
        engine._conditioned_inputs(frontend, 'a', 'neutral', source, 24000)
    assert len(engine._reference_cache) == engine._REFERENCE_CACHE_LIMIT
    engine._conditioned_inputs(frontend, 'b', 'review', references[-1], 24000)
    assert len(decodes) == engine._REFERENCE_CACHE_LIMIT + 1
    engine._conditioned_inputs(frontend, 'c', 'review', references[0], 24000)
    assert len(decodes) == engine._REFERENCE_CACHE_LIMIT + 2
    assert len(engine._reference_cache) == engine._REFERENCE_CACHE_LIMIT


@pytest.mark.parametrize('cuda', [False, True])
def test_acceleration_requires_available_cuda_and_keeps_cpu_float32(cuda):
    matmul = SimpleNamespace(allow_tf32=False)
    cudnn = SimpleNamespace(allow_tf32=False)
    torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: cuda),
                            backends=SimpleNamespace(cuda=SimpleNamespace(matmul=matmul), cudnn=cudnn))
    assert engine._device_options(torch) == {'device': 'cuda' if cuda else 'cpu', 'fp16': cuda}
    assert matmul.allow_tf32 is cuda and cudnn.allow_tf32 is cuda


def test_long_script_chunking_preserves_words_without_quadratic_front_pops():
    text = ('Nyob zoo. Kuv hais lus Hmoob! ' * 35000)[:engine.MAX_SCRIPT_CHARACTERS]
    chunks = list(engine._sentences(text))
    assert len(chunks) > 1000
    assert all(0 < len(chunk) <= 220 for chunk in chunks)
    assert ' '.join(chunks).split() == text.split()
    assert all(len(chunk) <= 220 for chunk in engine._sentences('x' * 10000))


@pytest.fixture
def fake_inference(monkeypatch, tmp_path):
    np = pytest.importorskip('numpy')
    torch = pytest.importorskip('torch')
    chunks = []
    frontend = Frontend()

    class Backend:
        def tts(self, **kwargs):
            chunks.append(kwargs)
            yield {'tts_speech': torch.from_numpy(np.sin(np.arange(2400) * .1).astype('float32'))}
    monkeypatch.setattr(engine, 'availability', lambda: {'ready': True})
    monkeypatch.setattr(engine, '_load_engine', lambda root: (frontend, Backend(), 24000))
    monkeypatch.setattr(engine, '_conditioned_inputs', lambda *args, **kwargs: {})
    return chunks


def test_long_output_streams_chunks_and_reports_real_completed_work(tmp_path, monkeypatch, fake_inference):
    np = pytest.importorskip('numpy')

    def no_concatenate(*args, **kwargs):
        raise AssertionError('Long-form generation must not concatenate all audio in RAM')
    monkeypatch.setattr(np, 'concatenate', no_concatenate)
    progress = []
    target = tmp_path / 'voice.wav'
    result = engine.synthesize('Nyob zoo. ' * 500, tmp_path / 'source.mp3', emotion='review',
                               output_path=target, progress=progress.append)
    assert result == target and target.is_file()
    assert len(fake_inference) > 1
    with wave.open(str(target)) as audio:
        assert audio.getnframes() == len(fake_inference) * (2400 + 3600)
        assert audio.getframerate() == 24000 and audio.getsampwidth() == 2
    values = [item['progress'] for item in progress]
    assert values == sorted(values) and values[-1] == 99
    completed = [item['completed_units'] for item in progress]
    assert completed == sorted(completed) and completed[-1] == len(fake_inference)
    assert progress[-1]['generated_seconds'] == pytest.approx(len(fake_inference) * .25)
    assert not list(tmp_path.glob('.hmong-voice-*.part'))


def test_generation_failure_preserves_existing_output_and_removes_partial(tmp_path, monkeypatch, fake_inference):
    target = tmp_path / 'voice.wav'
    target.write_bytes(b'old-complete-audio')
    # A tiny output limit reproduces the real RIFF/24-hour protection without
    # allocating a 4 GB test artifact.
    monkeypatch.setattr(engine, 'MAX_OUTPUT_SECONDS', .05)
    with pytest.raises(engine.EngineError, match='24 giờ'):
        engine.synthesize('Nyob zoo.', tmp_path / 'source.mp3', output_path=target)
    assert target.read_bytes() == b'old-complete-audio'
    assert not list(tmp_path.glob('.hmong-voice-*.part'))


def test_script_limit_is_one_million_before_model_loading(monkeypatch, tmp_path):
    def unavailable():
        raise AssertionError('Invalid text must be rejected before model loading')
    monkeypatch.setattr(engine, 'availability', unavailable)
    with pytest.raises(engine.EngineError, match='1.000.000'):
        engine.synthesize('x' * (engine.MAX_SCRIPT_CHARACTERS + 1), tmp_path / 'voice.mp3')


def test_windows_temporary_file_cleanup_failure_does_not_lock_next_job(tmp_path, monkeypatch, fake_inference):
    original_unlink = Path.unlink

    def windows_locked_temporary(path, *args, **kwargs):
        if path.name.startswith('.hmong-voice-'):
            raise PermissionError('Windows antivirus holds owned temp path')
        return original_unlink(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'unlink', windows_locked_temporary)
    first = engine.synthesize('Nyob zoo.', tmp_path / 'source.mp3', output_path=tmp_path / 'first.wav')
    second = engine.synthesize('Zoo siab.', tmp_path / 'source.mp3', output_path=tmp_path / 'second.wav')
    assert first.is_file() and second.is_file()
    assert not engine._lock.locked()
