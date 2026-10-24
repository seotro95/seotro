"""Failure-mode checks for the offline native adapter, without model weights.

Small tensor probes exercise the inference boundary. These checks cannot
establish Hmong pronunciation, speaker similarity or production throughput.
"""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace
import wave

import pytest

import hmong_native as native


def test_import_and_availability_are_lightweight_and_offline():
    source = """
import os, sys, urllib.request
os.environ['HMOOB_DEVICE'] = 'cpu'
def blocked(*args, **kwargs):
    raise AssertionError('network is forbidden')
urllib.request.urlopen = blocked
import hmong_native
hmong_native.verify_models = lambda *args: ('verified fixture',)
hmong_native.importlib.util.find_spec = lambda name: object()
status = hmong_native.availability()
assert status['ready']
assert status['precision'] == 'fp32'
assert status['quality_steps'] == {}
assert status['dialect_verified'] is False
assert status['target_30x_verified'] is False
assert not any(name in sys.modules for name in ('torch', 'torchaudio', 'numpy', 'librosa'))
"""
    result = subprocess.run([sys.executable, '-c', source], cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr


def test_basic_cleaning_keeps_every_rpa_tone_letter_and_target_word():
    text = '  UA\tTHAJ  QAB\nFAIB ROV RIS.\nPOB POJ POS POV POM POG POD PO '
    assert native.validate_text(text) == 'ua thaj qab faib rov ris. pob poj pos pov pom pog pod po'
    assert native.validate_text('NYOB ZOO, “KUV ZOO”…') == 'nyob zoo, "kuv zoo"...'


@pytest.mark.parametrize('dash', ['-', '‐', '‑', '‒', '–', '—', '―', '−'])
def test_written_hyphens_keep_word_boundaries_and_every_rpa_tone_letter(dash):
    text = f'UA{dash}THAJ QAB{dash}FAIB ROV{dash}RIS. POB{dash}POJ POS{dash}POV POM{dash}POG{dash}POD{dash}PO'
    assert native.validate_text(text) == 'ua thaj qab faib rov ris. pob poj pos pov pom pog pod po'
    # General/source normalization is deliberately unchanged for other engines.
    assert native.normalize_text(f'POB{dash}POJ') == 'POB-POJ'


@pytest.mark.parametrize('text', ['Kuv 123', 'Kuv @ zoo', 'Kuv_zoo', 'Nyob 😀', 'Kuv ꟽ', 'Nyob zòo'])
def test_unsupported_text_is_rejected_instead_of_dropping_characters(text):
    with pytest.raises(native.EngineError):
        native.validate_text(text)


@pytest.mark.parametrize('field,value', [
    ('text', None), ('text', ''), ('text', '  '), ('text', 'a' * 401), ('text', '...'),
    ('text', 'ua2'), ('reference_text', None), ('reference_text', ''),
    ('reference_text', 'a' * 2001), ('reference_text', 'Nyob ꟽ'),
    ('speed', True), ('speed', None), ('speed', '1'), ('speed', 0), ('speed', .49),
    ('speed', 2.01), ('speed', math.nan), ('speed', math.inf),
    ('quality', 'unknown'), ('quality', []),
])
def test_invalid_requests_fail_before_loading_weights(monkeypatch, field, value):
    engine = native.SpeechEngine()
    monkeypatch.setattr(engine, '_load', lambda: pytest.fail('Invalid input must not load weights'))
    options = dict(text='Nyob zoo.', reference_path='missing.wav', reference_text='Nyob zoo.', speed=1, quality='fast')
    options[field] = value
    with pytest.raises(native.EngineError):
        engine.synthesize(**options)


@pytest.fixture
def fake_loader(tmp_path, monkeypatch):
    """Keep deserialization and strict-load failures observable without Torch."""
    monkeypatch.setenv('HMOOB_DEVICE', 'cpu')
    monkeypatch.setenv('HMOOB_PRECISION', 'auto')
    config = {'data': {'sampling_rate': 22050, 'filter_length': 1024,
                       'hop_length': 256, 'n_speakers': 0},
              'train': {'segment_size': 8192}, 'model': {}}
    for relative in ('native-vits/config.json', 'openvoice-v2/config.json'):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config), encoding='utf-8')
    state = SimpleNamespace(integrity=('first',), fail=None, loads=[], constructions=[], cuda=False)

    class Network:
        def __init__(self, name):
            self.name = name
            self.dec = SimpleNamespace(remove_weight_norm=lambda: None)
            state.constructions.append(name)

        def load_state_dict(self, weights, strict):
            assert weights == {'pinned': self.name}
            assert strict is True, 'A partial checkpoint must never be accepted'
            if state.fail == self.name:
                raise RuntimeError('Missing or unexpected checkpoint keys')

        def eval(self):
            return self

        def to(self, device):
            self.device = device
            return self

    def loader(path, *, map_location, weights_only):
        assert map_location == 'cpu' and weights_only is True
        name = {'G_60000.pth': 'native', 'converter.pth': 'converter', 'model.pth': 'watermark'}[path.name]
        state.loads.append(name)
        weights = {'pinned': name}
        return weights if name == 'watermark' else {'model': weights}

    torch = ModuleType('torch')
    torch.cuda = SimpleNamespace(is_available=lambda: state.cuda, empty_cache=lambda: None)
    torch.set_num_threads = lambda count: None
    torch.load = loader
    monkeypatch.setitem(sys.modules, 'torch', torch)
    for module_name, export, name in (
        ('hmong_native_vendor.vits.models', 'SynthesizerTrn', 'native'),
        ('hmong_native_vendor.openvoice.models', 'SynthesizerTrn', 'converter'),
        ('hmong_native_vendor.watermark.models.my_model', 'Model', 'watermark'),
    ):
        module = ModuleType(module_name)
        setattr(module, export, lambda *args, _name=name, **kwargs: Network(_name))
        monkeypatch.setitem(sys.modules, module_name, module)
    monkeypatch.setattr(native, 'model_directory', lambda: tmp_path)
    monkeypatch.setattr(native, 'verify_models', lambda root: state.integrity)
    return state


@pytest.mark.parametrize('failure', ['native', 'converter', 'watermark'])
def test_strict_checkpoint_failure_leaves_no_partially_ready_engine(fake_loader, failure):
    state = fake_loader
    state.fail = failure
    engine = native.SpeechEngine()
    engine._reference, engine._reference_key = object(), ('old reference',)
    engine._reference_cache[('old model',)] = engine._reference
    with pytest.raises(RuntimeError, match='checkpoint keys'):
        engine._load()
    assert engine._model is None and engine._model_key is None
    assert engine._reference is None and engine._reference_key is None
    assert not engine._reference_cache
    assert state.loads[-1] == failure
    state.fail = None
    assert engine._load().backend == 'vits_openvoice_v2'


def test_loaded_networks_are_reused_until_integrity_or_device_changes(fake_loader, monkeypatch):
    state = fake_loader
    engine = native.SpeechEngine()
    first = engine._load()
    engine._reference, engine._reference_key = object(), ('reference',)
    engine._reference_cache[('reference',)] = engine._reference
    assert engine._load() is first
    assert engine._reference_cache
    monkeypatch.setenv('HMOOB_PRECISION', 'fp32')
    assert engine._load() is first  # auto already uses the same FP32 computation.
    assert state.loads == ['native', 'converter', 'watermark']
    state.integrity = ('new verified bytes',)
    second = engine._load()
    assert second is not first and engine._reference is None
    assert not engine._reference_cache
    engine._reference_cache[('second reference',)] = object()
    state.cuda = True
    monkeypatch.setenv('HMOOB_DEVICE', 'cuda')
    assert engine._load() is not second
    assert engine.device == 'cuda' and len(state.loads) == 9
    assert not engine._reference_cache


def write_reference(path, *, rate=24000, channels=1, width=2, seconds=3, silence=False):
    import array
    frames = int(rate * seconds)
    if width == 2:
        samples = array.array('h', (0 if silence else int(5000 * math.sin(index / 17))
                                  for index in range(frames * channels)))
        data = samples.tobytes()
    else:
        data = b'\x80' * frames * channels
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(channels)
        output.setsampwidth(width)
        output.setframerate(rate)
        output.writeframes(data)


@pytest.mark.parametrize('options', [{'seconds': 2}, {'seconds': 9}, {'channels': 2}, {'rate': 22050}, {'width': 1}])
def test_invalid_reference_format_or_duration_is_rejected(tmp_path, options):
    path = tmp_path / 'reference.wav'
    write_reference(path, **options)
    with pytest.raises(native.EngineError):
        native.SpeechEngine()._prepare_reference(path, 'Nyob zoo.', SimpleNamespace())


def test_reference_silence_is_rejected_and_same_metadata_edit_reextracts_embedding(tmp_path, monkeypatch):
    torch = pytest.importorskip('torch')
    pytest.importorskip('soxr')
    path = tmp_path / 'reference.wav'
    write_reference(path, silence=True)
    engine = native.SpeechEngine()
    engine.device = 'cpu'
    embeddings = []
    def embed(spec):
        embeddings.append(spec.detach().clone())
        return spec.mean(dim=1)
    model = SimpleNamespace(converter=SimpleNamespace(ref_enc=embed))
    monkeypatch.setattr(engine, '_spectrogram', lambda samples, model: samples.unsqueeze(1))
    monkeypatch.setattr(native, '_file_fingerprint', lambda *args: ('unchanged metadata',))
    with pytest.raises(native.EngineError, match='im lặng'):
        engine._prepare_reference(path, 'Nyob zoo.', model)
    assert not embeddings and engine._reference_key is None
    write_reference(path)
    original = engine._prepare_reference(path, 'Nyob zoo.', model)
    assert engine._prepare_reference(path, 'Nyob zoo.', model) is original and len(embeddings) == 1
    stat = path.stat()
    data = bytearray(path.read_bytes())
    data[-2:] = b'\xff\x7f'
    path.write_bytes(data)
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert engine._prepare_reference(path, 'Nyob zoo.', model) is not original
    assert len(embeddings) == 2  # A content digest catches even unreliable change-time metadata.


@pytest.fixture
def cached_reference_encoder(tmp_path, monkeypatch):
    pytest.importorskip('torch')
    pytest.importorskip('soxr')
    path = tmp_path / 'reference.wav'
    write_reference(path)
    engine = native.SpeechEngine()
    engine.device = 'cpu'
    engine._model_key = ('verified model bytes', 'cpu', 'fp32')
    embeddings = []

    def embed(spec):
        result = spec.mean(dim=1)
        embeddings.append(result)
        return result

    model = SimpleNamespace(converter=SimpleNamespace(ref_enc=embed))
    monkeypatch.setattr(engine, '_spectrogram', lambda samples, model: samples.unsqueeze(1))
    return engine, model, path, embeddings


def test_switching_back_to_an_exact_voice_reuses_its_embedding(cached_reference_encoder, tmp_path):
    engine, model, first_path, embeddings = cached_reference_encoder
    second_path = tmp_path / 'second.wav'
    second_path.write_bytes(first_path.read_bytes())
    first = engine._prepare_reference(first_path, 'Nyob zoo.', model)
    second = engine._prepare_reference(second_path, 'Kuv nyob ntawm no.', model)
    assert second is not first
    assert engine._prepare_reference(first_path, 'Nyob zoo.', model) is first
    assert engine._prepare_reference(second_path, 'Kuv nyob ntawm no.', model) is second
    assert len(embeddings) == 2 and len(engine._reference_cache) == 2


def test_reference_cache_binds_exact_words_and_loaded_model(cached_reference_encoder):
    engine, model, path, embeddings = cached_reference_encoder
    original = engine._prepare_reference(path, 'Nyob zoo.', model)
    edited_words = engine._prepare_reference(path, 'Nyob zoo os.', model)
    assert edited_words is not original
    assert engine._prepare_reference(path, 'Nyob zoo.', model) is original
    engine._model_key = ('replacement verified model bytes', 'cpu', 'fp32')
    assert engine._prepare_reference(path, 'Nyob zoo.', model) is not original
    assert len(embeddings) == 3


def test_reference_cache_is_bounded_and_evicts_the_least_recent_voice(cached_reference_encoder):
    engine, model, path, embeddings = cached_reference_encoder
    originals = [engine._prepare_reference(path, f'Nyob zoo {index}.', model)
                 for index in range(native.REFERENCE_CACHE_SIZE)]
    assert engine._prepare_reference(path, 'Nyob zoo 0.', model) is originals[0]
    engine._prepare_reference(path, 'Kuv tuaj tshiab.', model)
    assert len(engine._reference_cache) == native.REFERENCE_CACHE_SIZE
    assert engine._prepare_reference(path, 'Nyob zoo 0.', model) is originals[0]
    assert engine._prepare_reference(path, 'Nyob zoo 1.', model) is not originals[1]
    assert len(embeddings) == native.REFERENCE_CACHE_SIZE + 2
    assert len(engine._reference_cache) == native.REFERENCE_CACHE_SIZE


def test_failed_reference_encoding_does_not_cache_a_failed_voice(cached_reference_encoder):
    engine, model, path, embeddings = cached_reference_encoder
    original = engine._prepare_reference(path, 'Nyob zoo.', model)
    encoder = model.converter.ref_enc

    def failed_encoder(spec):
        raise RuntimeError('Reference encoding failed')

    model.converter.ref_enc = failed_encoder
    with pytest.raises(RuntimeError, match='Reference encoding failed'):
        engine._prepare_reference(path, 'Kuv rov los.', model)
    assert len(engine._reference_cache) == 1
    assert engine._reference is original
    assert engine._prepare_reference(path, 'Nyob zoo.', model) is original
    model.converter.ref_enc = encoder
    assert engine._prepare_reference(path, 'Kuv rov los.', model) is not original
    assert len(embeddings) == 2 and len(engine._reference_cache) == 2


def test_reference_encoding_decodes_the_exact_hashed_bytes(cached_reference_encoder, monkeypatch):
    engine, model, path, embeddings = cached_reference_encoder
    original_content = path.read_bytes()
    read_bytes = Path.read_bytes

    def replace_after_read(selected):
        content = read_bytes(selected)
        if selected == path:
            write_reference(path, silence=True)
        return content

    monkeypatch.setattr(Path, 'read_bytes', replace_after_read)
    engine._prepare_reference(path, 'Nyob zoo.', model)
    assert len(embeddings) == 1  # Replacement silence was never encoded.
    assert engine._reference_key[-2] == native.hashlib.sha256(original_content).hexdigest()


@pytest.fixture
def tensor_pipeline(monkeypatch):
    torch = pytest.importorskip('torch')
    state = SimpleNamespace(source=torch.full((1, 1, 20000), .1), audio=torch.full((20000,), .2),
                            inference=[], conversions=[], watermark_calls=0)
    engine = native.SpeechEngine()
    engine.device = 'cpu'
    target = torch.ones((1, 1, 1))
    def infer(tokens, lengths, **kwargs):
        state.inference.append((tokens.clone(), lengths.clone(), kwargs))
        return (state.source,)
    def convert(spec, frame_lengths, **kwargs):
        state.conversions.append(kwargs)
        return (state.audio.unsqueeze(0).unsqueeze(0),)
    def encode(signal, message):
        state.watermark_calls += 1
        assert message.shape == (1, 32)
        return signal * .95
    model = SimpleNamespace(native=SimpleNamespace(infer=infer),
        converter=SimpleNamespace(ref_enc=lambda spec: torch.zeros((1, 1)), voice_conversion=convert),
        watermark=SimpleNamespace(encode=encode), native_config={'data': {'hop_length': 256}})
    monkeypatch.setattr(engine, '_load', lambda: model)
    monkeypatch.setattr(engine, '_prepare_reference', lambda *args: target)
    monkeypatch.setattr(engine, '_spectrogram', lambda samples, model: samples.unsqueeze(1))
    return torch, engine, state, target


def test_native_pipeline_preserves_target_tokens_and_applies_requested_speed(tensor_pipeline):
    torch, engine, state, target = tensor_pipeline
    samples, rate = engine.synthesize('UA, THAJ, QAB, FAIB, ROV, RIS.', 'ref.wav', 'Nyob zoo.', speed=1.25)
    tokens, lengths, options = state.inference[0]
    decoded = ''.join(native.symbols[value] for value in tokens[0].tolist() if value)
    assert decoded == 'ua, thaj, qab, faib, rov, ris.'
    assert lengths.tolist() == [tokens.shape[1]]
    assert options['length_scale'] == .8 and options['max_len'] > 0
    assert state.conversions[0]['sid_tgt'] is target
    assert samples.dtype.name == 'float32' and rate == 22050 and len(samples) == 20000
    assert state.watermark_calls == 1


def test_hyphenated_native_input_uses_identical_tokens_to_spaced_words(tensor_pipeline):
    _, engine, state, _ = tensor_pipeline
    engine.synthesize('UA-THAJ, QAB–FAIB, ROV‑RIS.', 'ref.wav', 'Nyob zoo.')
    engine.synthesize('UA THAJ, QAB FAIB, ROV RIS.', 'ref.wav', 'Nyob zoo.')
    first, second = state.inference
    assert first[0].equal(second[0]) and first[1].equal(second[1])
    assert first[2] == second[2]


def test_short_word_keeps_its_natural_duration_without_padding_or_watermark(tensor_pipeline):
    torch, engine, state, _ = tensor_pipeline
    state.source, state.audio = torch.full((1, 1, 4096), .1), torch.full((4096,), .2)
    messages = []
    engine.set_progress_callback(messages.append)
    samples, rate = engine.synthesize('ua', 'ref.wav', 'Nyob zoo.')
    assert len(samples) == 4096 and rate == 22050
    assert state.watermark_calls == 0
    assert any('quá ngắn' in message for message in messages)


@pytest.mark.parametrize('failure', ['nonfinite-source', 'short-source', 'nonfinite-converter', 'silent-converter', 'long-converter'])
def test_invalid_inference_audio_never_returns_as_a_success(tensor_pipeline, failure):
    torch, engine, state, _ = tensor_pipeline
    if failure == 'nonfinite-source':
        state.source[0, 0, 0] = math.nan
    elif failure == 'short-source':
        state.source = torch.ones((1, 1, 1023))
    elif failure == 'nonfinite-converter':
        state.audio[0] = math.nan
    elif failure == 'silent-converter':
        state.audio.zero_()
    else:
        state.audio = torch.ones((native.MAX_SECONDS * native.SAMPLE_RATE + 1,))
    with pytest.raises(native.EngineError):
        engine.synthesize('Nyob zoo.', 'ref.wav', 'Nyob zoo.')
    if failure.endswith('source'):
        assert not state.conversions


@pytest.mark.parametrize('log_duration', [20., math.inf, math.nan])
def test_predicted_duration_is_bounded_before_alignment_allocation(monkeypatch, log_duration):
    torch = pytest.importorskip('torch')
    from hmong_native_vendor.vits import models
    x, mask = torch.ones((1, 2, 3)), torch.ones((1, 1, 3))
    probe = SimpleNamespace(n_speakers=0, use_sdp=False,
        enc_p=lambda *args: (x, torch.zeros_like(x), torch.zeros_like(x), mask),
        dp=lambda *args, **kwargs: torch.full_like(mask, log_duration))
    monkeypatch.setattr(models.commons, 'sequence_mask', lambda *args, **kwargs:
                        pytest.fail('Reject duration before allocating an alignment mask'))
    with pytest.raises(ValueError, match='bounded inference duration'):
        models.SynthesizerTrn.infer(probe, torch.ones((1, 3), dtype=torch.long), torch.tensor([3]), max_len=100)
