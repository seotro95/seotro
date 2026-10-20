import io
import math
import os
from pathlib import Path
from unittest.mock import Mock, patch
import wave

import pytest

import cloning_engine as engine


def make_reference(path, seconds=4):
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(b'\x01\x01' * int(seconds * 8000))
    return path


def model_files(tmp_path):
    checkpoint = tmp_path / 'hmong.safetensors'
    vocab = tmp_path / 'vocab.txt'
    vocoder = tmp_path / 'vocoder'
    vocoder.mkdir()
    for path in (checkpoint, vocab, vocoder / 'config.yaml', vocoder / 'pytorch_model.bin'):
        path.write_bytes(b'test fixture; not model weights')
    return {'HMONG_F5_CHECKPOINT': str(checkpoint), 'HMONG_F5_VOCAB': str(vocab),
            'HMONG_F5_VOCODER': str(vocoder)}


def test_status_requires_explicit_local_artifacts():
    with patch.dict(os.environ, {}, clear=True), patch.object(engine, '_dependencies', return_value=False):
        state = engine.availability()
    assert not state['ready']
    assert not state['configured']
    assert not state['dialect_verified']
    assert 'HMONG_F5_CHECKPOINT' in state['reason']


def test_partial_configuration_and_pickle_do_not_become_ready(tmp_path):
    settings = model_files(tmp_path)
    with patch.dict(os.environ, settings, clear=True), patch.object(engine, '_dependencies', return_value=True):
        assert engine.availability()['ready']
        assert not engine.availability()['dialect_verified']
        (Path(settings['HMONG_F5_VOCODER']) / 'pytorch_model.bin').unlink()
        assert not engine.availability()['ready']
    settings['HMONG_F5_CHECKPOINT'] = str(tmp_path / 'unsafe.pt')
    with patch.dict(os.environ, settings, clear=True):
        assert '.safetensors' in engine.availability()['reason']


def test_explicit_transcript_prevents_automatic_asr(tmp_path):
    reference = make_reference(tmp_path / 'ref.wav')
    with patch.object(engine, '_load_model') as load:
        with pytest.raises(engine.CloningError, match='bản chép'):
            engine.synthesize('Nyob zoo', 1, reference, '  ')
        load.assert_not_called()


@pytest.mark.parametrize('seconds', [2.9, 8.1, 25])
def test_reference_duration_is_not_silently_cropped(tmp_path, seconds):
    reference = make_reference(tmp_path / 'ref.wav', seconds)
    with pytest.raises(engine.CloningError, match='3–8 giây'):
        engine.synthesize('Nyob zoo', 1, reference, 'Nyob zoo')


def test_contract_uses_exact_reference_and_returns_decodable_wav(tmp_path):
    reference = make_reference(tmp_path / 'ref.wav')
    model = Mock()
    model.infer.return_value = ([math.sin(index * .1) * .3 for index in range(8000)], 8000, None)
    with patch.object(engine, 'availability', return_value={'ready': True}), patch.object(engine, '_load_model', return_value=model):
        data = engine.synthesize(' Nyob zoo. ', .8, reference, ' Kuv hais lus Hmoob. ')
    call = model.infer.call_args.kwargs
    assert call['ref_file'] == str(reference)
    assert call['ref_text'] == 'Kuv hais lus Hmoob.'
    assert call['gen_text'] == 'Nyob zoo.'
    assert call['speed'] == .8
    assert call['progress'] is None
    with wave.open(io.BytesIO(data)) as output:
        assert output.getnchannels() == 1
        assert output.getsampwidth() == 2
        assert output.getframerate() == 8000
        assert output.getnframes() == 8000
        assert set(output.readframes(8000)) != {0}


@pytest.mark.parametrize('samples', [[], [0.0] * 20, [float('nan')], [float('inf')], [[.1, .2]]])
def test_invalid_generated_audio_is_never_reported_as_success(samples):
    with pytest.raises(engine.CloningError):
        engine._wav(samples, 24000)


def test_inference_exception_is_sanitized_and_lock_is_released(tmp_path):
    reference = make_reference(tmp_path / 'ref.wav')
    model = Mock()
    model.infer.side_effect = RuntimeError('private/path and untrusted details')
    with patch.object(engine, 'availability', return_value={'ready': True}), patch.object(engine, '_load_model', return_value=model):
        with pytest.raises(engine.CloningError) as caught:
            engine.synthesize('Nyob zoo', 1, reference, 'Kuv hais lus Hmoob')
    assert 'private/path' not in str(caught.value)
    assert engine._lock.acquire(blocking=False)
    engine._lock.release()


def test_local_model_constructor_does_not_use_implicit_downloads(tmp_path):
    settings = model_files(tmp_path)
    arguments = {name: value for name, value in zip(('checkpoint', 'vocab', 'vocoder'), settings.values())}
    arguments.update(model='F5TTS_Base', device='cpu')
    factory = Mock()
    torch = Mock()
    with patch.dict('sys.modules', {'torch': torch, 'f5_tts': Mock(), 'f5_tts.api': Mock(F5TTS=factory)}):
        with patch.object(engine, '_model', None), patch.object(engine, '_model_key', None):
            first = engine._load_model(arguments)
            assert engine._load_model(arguments) is first
            factory.assert_called_once_with(model='F5TTS_Base', ckpt_file=arguments['checkpoint'],
                                            vocab_file=arguments['vocab'], vocoder_local_path=arguments['vocoder'],
                                            device='cpu')
            torch.set_num_threads.assert_called_once()
