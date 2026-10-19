import hashlib
import io
import json
from pathlib import Path
import wave

import pytest

import cosy_engine as engine


def snapshot(tmp_path):
    entries = []
    for relative in (*engine._REQUIRED_FILES, 'CosyVoice/cosyvoice/__init__.py'):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        content = b'' if relative.endswith('__init__.py') else relative.encode()
        path.write_bytes(content)
        entries.append({'path': relative, 'size': len(content),
                        'sha256': hashlib.sha256(content).hexdigest()})
    marker = {'repository': engine.REPOSITORY, 'revision': engine.REVISION, 'files': entries}
    (tmp_path / engine.MARKER).write_text(json.dumps(marker))
    return marker


def test_verified_snapshot_accepts_empty_python_packages_and_detects_tampering(tmp_path, monkeypatch):
    snapshot(tmp_path)
    monkeypatch.setattr(engine, '_verified', None)
    engine._verify_snapshot(tmp_path)
    path = tmp_path / engine._REQUIRED_FILES[0]
    content = path.read_bytes()
    path.write_bytes(b'x' + content[1:])
    # Availability remains a cheap size check. Actual model loading must hash.
    assert engine._manifest(tmp_path)
    with pytest.raises(engine.EngineError, match='kiểm tra'):
        engine._verify_snapshot(tmp_path)


def test_snapshot_requires_all_inference_files_and_pinned_revision(tmp_path):
    marker = snapshot(tmp_path)
    marker['revision'] = 'another-revision'
    (tmp_path / engine.MARKER).write_text(json.dumps(marker))
    with pytest.raises(engine.EngineError):
        engine._manifest(tmp_path)
    marker['revision'] = engine.REVISION
    marker['files'].pop(0)
    (tmp_path / engine.MARKER).write_text(json.dumps(marker))
    with pytest.raises(engine.EngineError):
        engine._manifest(tmp_path)


def test_manifest_rejects_path_escape(tmp_path):
    marker = snapshot(tmp_path)
    marker['files'][0]['path'] = '../outside'
    (tmp_path / engine.MARKER).write_text(json.dumps(marker))
    with pytest.raises(engine.EngineError):
        engine._manifest(tmp_path)


def test_only_inference_yaml_nodes_are_retained_and_unknown_tags_rejected(tmp_path):
    pytest.importorskip('yaml')
    path = tmp_path / 'config.yaml'
    lines = [f'{key}: 1' for key in sorted(engine._CONFIG_KEYS - {'llm'})]
    lines += ['llm: !new:cosyvoice.llm.llm.CosyVoice3LM {}',
              '__set_seed: !apply:untrusted.code []',
              'parquet_opener: !name:cosyvoice.dataset.processor.parquet_opener',
              'hifigan: !new:untrusted.TrainingObject {}']
    path.write_text('\n'.join(lines))
    result = engine._inference_config(path)
    assert 'CosyVoice3LM' in result
    assert 'untrusted' not in result and 'dataset.processor' not in result
    path.write_text(path.read_text().replace('!new:cosyvoice.llm.llm.CosyVoice3LM', '!apply:untrusted.code'))
    with pytest.raises(engine.EngineError, match='chưa được kiểm tra'):
        engine._inference_config(path)


def test_weights_use_restricted_loader_and_never_rewrite_checkpoint(tmp_path):
    class Tensor:
        pass

    class FakeTorch:
        pass

    original = {'parameter': Tensor(), 'epoch': 1, 'step': 2}
    called = []
    FakeTorch.Tensor = Tensor

    def load(path, **kwargs):
        called.append(kwargs)
        return original
    FakeTorch.load = load
    path = tmp_path / 'llm.pt'
    path.write_bytes(b'unchanged-checkpoint')
    state = engine._weights(path, FakeTorch)
    assert called == [{'map_location': 'cpu', 'weights_only': True}]
    assert list(state) == ['parameter']
    assert original['epoch'] == 1 and original['step'] == 2
    assert path.read_bytes() == b'unchanged-checkpoint'


def test_reference_is_bounded_and_original_preserved(tmp_path):
    np = pytest.importorskip('numpy')
    if not engine.shutil.which('ffmpeg'):
        pytest.skip('FFmpeg is required for reference conversion')
    original = tmp_path / 'source.wav'
    converted = tmp_path / 'reference.wav'
    samples = np.sin(np.arange(12 * 32000) * .05).astype('float32') * .3
    original.write_bytes(engine._wav(samples, 32000))
    digest = hashlib.sha256(original.read_bytes()).hexdigest()
    engine._decode_reference(original, converted)
    with wave.open(str(converted)) as wav:
        assert wav.getnchannels() == 1 and wav.getframerate() == 24000
        assert wav.getnframes() == 240000
    assert hashlib.sha256(original.read_bytes()).hexdigest() == digest


def test_instruct2_uses_reference_and_selected_style_without_transcript(tmp_path, monkeypatch):
    np = pytest.importorskip('numpy')
    torch = pytest.importorskip('torch')
    captured = []

    class Frontend:
        def frontend_instruct2(self, text, instruction, reference, rate, speaker):
            captured.append((text, instruction, reference, rate, speaker))
            return {'test_input': True}

    class Backend:
        def tts(self, **kwargs):
            assert kwargs == {'test_input': True, 'stream': False, 'speed': 1.2}
            yield {'tts_speech': torch.from_numpy(np.sin(np.arange(2400) * .1).astype('float32'))}

    monkeypatch.setattr(engine, 'availability', lambda: {'ready': True})
    monkeypatch.setattr(engine, '_decode_reference', lambda source, target: Path(target).write_bytes(b'reference'))
    monkeypatch.setattr(engine, '_load_engine', lambda root: (Frontend(), Backend(), 24000))
    result = engine.synthesize('Nyob zoo.', tmp_path / 'source.mp3', emotion='review', speed=1.2)
    with wave.open(io.BytesIO(result)) as wav:
        assert wav.getnframes() > 2400 and wav.getframerate() == 24000
    assert len(captured) == 1
    text, instruction, reference, rate, speaker = captured[0]
    assert text == 'Nyob zoo.' and 'White Hmong RPA' in instruction
    assert 'product review' in instruction and instruction.endswith('<|endofprompt|>')
    assert reference.endswith('reference.wav') and rate == 24000 and speaker == ''


@pytest.mark.parametrize('values', [[], [0, 0], [float('nan')], [float('inf')]])
def test_invalid_generated_audio_is_not_reported_as_success(values):
    pytest.importorskip('numpy')
    with pytest.raises(engine.EngineError):
        engine._wav(values, 24000)
