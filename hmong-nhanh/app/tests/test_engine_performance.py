"""Guard quality, actual device choice, bounded inference and reference reuse."""
from types import SimpleNamespace
from unittest.mock import Mock, patch
import wave
import pytest
import cloning_engine as engine


def make_reference(path):
    with wave.open(str(path), 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(b'\x01\x04' * (24000 * 4))
    return path


@pytest.mark.parametrize('quality,steps', [('draft', 4), ('fast', 8), ('balanced', 16), ('quality', 32)])
def test_quality_controls_real_inference_steps(tmp_path, quality, steps):
    path = make_reference(tmp_path / 'sample.wav')
    prepared = {'seconds': 4, 'text': 'Kuv hais lus Hmoob rau koj. '}
    with patch.object(engine, 'availability', return_value={'ready': True}), patch.object(engine, '_load_model') as load, patch.object(engine, '_prepare_reference', return_value=prepared), patch.object(engine, '_infer_one', return_value=engine._wav([.1] * 240, 24000)) as infer:
        engine.synthesize('Nyob zoo.', 1, path, 'Kuv hais lus Hmoob rau koj.', quality=quality)
    assert infer.call_args.args[-1] == steps


def test_bad_quality_rejected_before_loading(tmp_path):
    with patch.object(engine, '_load_model') as load:
        with pytest.raises(engine.CloningError, match='chất lượng'):
            engine.synthesize('Nyob zoo.', 1, tmp_path / 'not-used.wav', 'Kuv hais lus Hmoob.', quality='fake30x')
    load.assert_not_called()


@pytest.mark.parametrize('cuda,mps,expected', [(True,True,'cuda'), (False,True,'mps'), (False,False,'cpu')])
def test_auto_uses_available_accelerator(cuda,mps,expected):
    torch = fake_torch(cuda=cuda, mps=mps)
    assert engine._resolve_device('auto', torch) == expected
    assert engine._resolve_device('cpu', torch) == 'cpu'
    if not cuda:
        with pytest.raises(engine.CloningError, match='CUDA'):
            engine._resolve_device('cuda', torch)


def fake_torch(cuda=True, mps=False, capability=(8, 6), version='2.6.0+cu124'):
    return SimpleNamespace(
        __version__=version,
        cuda=SimpleNamespace(is_available=Mock(return_value=cuda),
                             get_device_capability=Mock(return_value=capability)),
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: mps)),
        zeros=Mock())


def test_visible_unsupported_blackwell_falls_back_and_explicit_cuda_errors():
    torch = fake_torch(capability=(12, 0))
    assert engine._resolve_device('auto', torch) == 'cpu'
    with pytest.raises(engine.CloningError, match='Blackwell'):
        engine._resolve_device('cuda', torch)
    torch.zeros.assert_not_called()


def test_driver_visible_but_cuda_kernel_failure_is_not_reported_as_usable():
    torch = fake_torch()
    torch.zeros.side_effect = RuntimeError('no kernel image is available')
    assert engine._resolve_device('auto', torch) == 'cpu'
    with pytest.raises(engine.CloningError, match='chưa chạy được CUDA'):
        engine._resolve_device('cuda', torch)
    assert torch.zeros.call_count == 1


def test_cuda_probe_runs_once_but_does_not_block_newer_compatible_blackwell():
    torch = fake_torch(capability=(12, 0), version='2.8.0+cu128')
    for _ in range(5):
        assert engine._resolve_device('auto', torch) == 'cuda'
    torch.zeros.assert_called_once_with(1, device='cuda')
    torch.zeros.return_value.add_.return_value.item.assert_called_once()


def test_explicit_cpu_does_not_probe_cuda_at_all():
    torch = fake_torch()
    torch.cuda.is_available.side_effect = RuntimeError('broken driver')
    assert engine._resolve_device('cpu', torch) == 'cpu'
    torch.cuda.is_available.assert_not_called()
    torch.zeros.assert_not_called()


def test_reference_cache_is_invalidated_by_voice_text_or_model(tmp_path, monkeypatch):
    torch = pytest.importorskip('torch')
    sf = pytest.importorskip('soundfile')
    monkeypatch.setattr(engine, '_reference', None)
    monkeypatch.setattr(engine, '_reference_key', None)
    monkeypatch.setattr(engine, '_model_key', ('weights-v1',))
    voice1=make_reference(tmp_path/'male.wav')
    voice2=make_reference(tmp_path/'female.wav')
    model=SimpleNamespace(device='cpu',ema_model=SimpleNamespace(mel_spec=Mock(side_effect=lambda audio:torch.ones(1,100,audio.shape[-1]//256))))
    text='Kuv hais lus Hmoob.'
    with patch.object(sf,'read',wraps=sf.read) as read:
        first=engine._prepare_reference(model,voice1,text,engine._reference_identity(voice1,text))
        assert engine._prepare_reference(model,voice1,text,engine._reference_identity(voice1,text)) is first
        assert read.call_count==1
        assert model.ema_model.mel_spec.call_count==1
        changed=engine._prepare_reference(model,voice2,text,engine._reference_identity(voice2,text))
        assert changed is not first
        engine._prepare_reference(model,voice2,text+' New.',engine._reference_identity(voice2,text+' New.'))
        monkeypatch.setattr(engine,'_model_key',('weights-v2',))
        engine._prepare_reference(model,voice2,text,engine._reference_identity(voice2,text))
        assert read.call_count==4
        assert model.ema_model.mel_spec.call_count==4
    # Adapter always uses the cached reference mel; it cannot switch to another voice.
    base=Mock()
    cached=object()
    proxy=engine._ConditionedModel(base,cached)
    proxy.sample(cond='waveform',text=['same voice'],steps=8)
    base.sample.assert_called_once_with(cond=cached,text=['same voice'],steps=8)


def test_direct_inference_submits_one_batch_and_preserves_parameters(monkeypatch):
    # A fake upstream isolates the contract; real inference is separately benchmarked.
    import sys
    upstream=Mock(return_value=iter([([.2]*240,24000,None)]))
    torch=SimpleNamespace(inference_mode=lambda:__import__('contextlib').nullcontext())
    monkeypatch.setitem(sys.modules,'torch',torch)
    monkeypatch.setitem(sys.modules,'f5_tts.infer.utils_infer',SimpleNamespace(infer_batch_process=upstream))
    prepared={'audio':('exact cached waveform',24000),'text':'exact transcript. ','conditioned_model':object()}
    model=SimpleNamespace(vocoder=object(),device='cuda',mel_spec_type='vocos')
    data=engine._infer_one(model,prepared,'Nyob zoo.',.8,4)
    call=upstream.call_args
    assert call.args[:3]==(prepared['audio'],prepared['text'],['Nyob zoo.'])
    assert call.kwargs['nfe_step']==4
    assert call.kwargs['speed']==.8
    assert call.kwargs['device']=='cuda'
    assert call.kwargs['cross_fade_duration']==0
    assert data[:4]==b'RIFF'
