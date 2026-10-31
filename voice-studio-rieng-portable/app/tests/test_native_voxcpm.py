"""VoxCPM2 keeps its own model, language mapping and PCM path through C ABI."""
import ctypes as C
import hashlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf

import fast_multilingual as backend
import native_synthesis as native
import native_voxcpm_model as models
from test_native_multilingual import FakeLibrary


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    data = tmp_path / 'data'
    model = data / 'models' / models.MODEL_DIRECTORY / models.MODEL_FILENAME
    model.parent.mkdir(parents=True)
    payload = b'GGUFsynthetic-native-voxcpm-test-weights'
    model.write_bytes(payload)
    record = {'schema': 1, 'backend': 'voxcpm_native',
              'repository': models.MODEL_REPOSITORY, 'revision': models.MODEL_REVISION,
              'native_source_revision': models.NATIVE_REVISION,
              'model_dir': models.MODEL_DIRECTORY, 'filename': models.MODEL_FILENAME,
              'size': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(),
              'quantization': 'q8_0'}
    (data / 'models' / models.MARKER_NAME).write_text(json.dumps(record))
    root = tmp_path / 'runtime-native'
    monkeypatch.setenv('VOICE_STUDIO_NATIVE_ROOT', str(root))
    name = 'audiocpp.dll' if sys.platform == 'win32' else ('libaudiocpp.dylib' if sys.platform == 'darwin' else 'libaudiocpp.so')
    for device in ('cpu', 'cuda'):
        library = root / device / name
        library.parent.mkdir(parents=True)
        library.write_bytes(('library-fixture-' + device).encode())
        manifest = {'schema': 1, 'revision': models.NATIVE_REVISION,
                    'families': ['omnivoice', 'voxcpm2'], 'device': device,
                    'sha256': {name: hashlib.sha256(library.read_bytes()).hexdigest()}}
        (library.parent / 'native-build.json').write_text(json.dumps(manifest))
    return data, model, record


def test_separate_model_is_ready_but_corrupt_same_size_weights_are_never_loaded(prepared):
    data, model, _ = prepared
    assert backend.is_ready(data, family='voxcpm2')
    assert backend.cuda_available(data, family='voxcpm2')
    assert not backend.is_ready(data)  # The VoxCPM2 marker cannot stand in for OmniVoice.
    assert models.prepared_model(data, verify=True)[0] == model
    payload = model.read_bytes()
    model.write_bytes(payload[:-1] + b'!')
    assert backend.is_ready(data, family='voxcpm2')
    with pytest.raises(ValueError, match='SHA256'):
        models.prepared_model(data, verify=True)


@pytest.mark.parametrize('field,value', [
    ('backend', 'omnivoice'), ('repository', 'other/model'), ('revision', 'a' * 40),
    ('native_source_revision', 'b' * 40), ('model_dir', '../elsewhere'),
    ('filename', 'model.gguf'), ('quantization', 'q4_k'), ('schema', True),
    ('size', True), ('sha256', 'not-a-checksum'),
])
def test_wrong_model_provenance_never_reports_ready(prepared, field, value):
    data, _, record = prepared
    record[field] = value
    (data / 'models' / models.MARKER_NAME).write_text(json.dumps(record))
    assert not backend.is_ready(data, family='voxcpm2')


@pytest.mark.parametrize('record', [None, [], True, 42, 'wrong'])
def test_malformed_model_record_cannot_crash_readiness(prepared, record):
    data, _, _ = prepared
    (data / 'models' / models.MARKER_NAME).write_text(json.dumps(record))
    assert not backend.is_ready(data, family='voxcpm2')


@pytest.mark.parametrize('field,value', [
    ('families', ['omnivoice']), ('families', 'voxcpm2'),
    ('revision', 'c' * 40), ('device', 'cpu'), ('sha256', {}),
])
def test_cuda_requires_matching_voxcpm_build_not_an_omni_only_library(prepared, field, value):
    data, _, _ = prepared
    library = backend.library_path('cuda', family='voxcpm2')
    path = library.parent / 'native-build.json'
    manifest = json.loads(path.read_text())
    manifest[field] = value
    path.write_text(json.dumps(manifest))
    assert backend.is_ready(data, device='cpu', family='voxcpm2')
    assert not backend.is_ready(data, device='cuda', family='voxcpm2')
    reference = data / 'reference.wav'
    reference.write_bytes(b'sample')
    with pytest.raises(ValueError, match='CUDA'):
        backend.create_synthesizer(reference, data, device='cuda', family='voxcpm2')


def test_damaged_native_library_is_rejected_before_any_child_starts(prepared, monkeypatch):
    data, _, _ = prepared
    library = backend.library_path('cpu', family='voxcpm2')
    payload = library.read_bytes()
    library.write_bytes(payload[:-1] + b'!')
    reference = data / 'reference.wav'
    reference.write_bytes(b'sample')
    def unexpected(*args, **kwargs):
        pytest.fail('A mismatched native library must not be executed')
    monkeypatch.setattr(backend, '_BackendClient', unexpected)
    synth = backend.create_synthesizer(reference, data, family='voxcpm2')
    with pytest.raises(ValueError, match='SHA256'):
        synth('Bonjour.', data / 'parts/output.wav')


@pytest.mark.parametrize('language,expected', [
    ('en-US', 'en'), ('en-GB', 'en'), ('ja', 'ja'), ('ko', 'ko'), ('th', 'th'),
    ('fr', 'fr'), ('ar', 'ar'), ('tl', 'tl'), ('no', 'no'), ('my', 'my'),
])
def test_voxcpm_language_map_is_not_the_omnivoice_map(language, expected):
    assert backend.language_code(language, family='voxcpm2') == expected


@pytest.mark.parametrize('language', ['ne', 'hmn', 'fil', 'arb', None, []])
def test_voxcpm_rejects_languages_outside_its_verified_catalog(language):
    with pytest.raises(ValueError, match='Ngôn ngữ'):
        backend.language_code(language, family='voxcpm2')


def test_one_voxcpm_model_is_reused_across_voices_languages_and_steps_without_asr(prepared, monkeypatch):
    data, _, _ = prepared
    created, calls = [], []
    class Client:
        def __init__(self, library, model, directory, threads, device, key, record):
            self.key = key
            self.process = SimpleNamespace(poll=lambda: None)
            self.execution = {'backend': 'voxcpm_native', 'model_family': 'voxcpm2', 'device': device}
            self.closed = False
            created.append(self)
        def synthesize(self, text, reference, output, steps, language, transcript):
            calls.append((reference.name, language, steps, transcript))
        def close(self): self.closed = True
    def no_asr(*args):
        pytest.fail('VoxCPM reference-only cloning does not need a transcript or recognizer')
    monkeypatch.setitem(sys.modules, 'native_transcript', SimpleNamespace(reference_transcript=no_asr))
    monkeypatch.setattr(backend, '_BackendClient', Client)
    monkeypatch.setattr(backend, '_client', None)
    references = [data / 'fr.wav', data / 'ja.wav']
    for path in references: path.write_bytes(b'public synthetic fixture')
    french = backend.create_synthesizer(references[0], data, family='voxcpm2', steps=4, language='fr')
    japanese = backend.create_synthesizer(references[1], data, family='voxcpm2', steps=10, language='ja')
    cuda = backend.create_synthesizer(references[0], data, family='voxcpm2', steps=8, device='cuda')
    try:
        french('Bonjour.', data / 'parts/a.wav')
        japanese('こんにちは。', data / 'parts/b.wav')
        french('Merci.', data / 'parts/c.wav')
        assert len(created) == 1
        cuda('Encore.', data / 'parts/d.wav')
        assert len(created) == 2 and created[0].closed
        assert calls == [('fr.wav', 'fr', 4, ''), ('ja.wav', 'ja', 10, ''),
                         ('fr.wav', 'fr', 4, ''), ('fr.wav', 'fr', 8, '')]
        assert backend.execution_info()['backend'] == 'voxcpm_native'
    finally:
        backend.close_backends()


@pytest.mark.parametrize('actual', [
    {'backend': 'omnivoice', 'model_family': 'voxcpm2', 'device': 'cuda'},
    {'backend': 'voxcpm_native', 'model_family': 'voxcpm2', 'device': 'cpu'},
    {'backend': 'voxcpm_native', 'model_family': 'omnivoice', 'device': 'cuda'},
])
def test_child_cannot_report_another_family_or_device_as_the_selected_one(actual):
    client = backend._BackendClient.__new__(backend._BackendClient)
    client.family, client.backend, client.device = 'voxcpm2', 'voxcpm_native', 'cuda'
    client.execution = {}
    with pytest.raises(ValueError, match='thiết bị'):
        client._execution(actual)


@pytest.mark.parametrize('language', ['ja', 'fr', 'ko', 'ar', 'tl'])
def test_voxcpm_c_abi_keeps_reference_and_resamples_48k_audio_without_changing_duration(tmp_path, language):
    reference = tmp_path / 'reference.wav'
    samples = (.15 * np.sin(np.arange(24000) * .023)).astype(np.float32)
    sf.write(reference, samples, 24000, subtype='FLOAT')
    waveform = (.2 * np.sin(2 * np.pi * 440 * np.arange(48000) / 48000)).astype(np.float32)
    session = native.NativeSession.__new__(native.NativeSession)
    session.family, session.threads, session.device = 'voxcpm2', 4, 'cuda'
    session.session, session.lib = C.c_void_p(7), FakeLibrary(waveform)
    session.info = {'backend': 'voxcpm_native', 'model_family': 'voxcpm2', 'device': 'cuda'}
    output = tmp_path / 'speech.wav'
    info = session.synthesize('Original requested text.', reference, output, steps=10, language=language)
    assert session.lib.text == 'Original requested text.' and session.lib.language == language
    assert np.array_equal(session.lib.reference, samples)
    assert session.lib.options == {'num_inference_steps': '10', 'guidance_scale': '2.0'}
    assert info['voxcpm_steps'] == 10 and info['backend'] == 'voxcpm_native'
    assert 'omnivoice_steps' not in info
    pcm, rate = sf.read(output)
    assert rate == 24000 and pcm.shape == (24000,)
    spectrum = np.abs(np.fft.rfft(pcm))
    assert np.fft.rfftfreq(len(pcm), 1/rate)[np.argmax(spectrum)] == pytest.approx(440, abs=1)
    assert session.lib.freed == ['result', 'request']


def test_voxcpm_protocol_constructs_only_requested_family_and_can_omit_transcript(tmp_path, monkeypatch):
    calls = []
    class Session:
        def __init__(self, data, threads, device, family, native_performance='off'):
            assert native_performance == 'off'
            calls.append((family, device))
        def synthesize(self, text, reference, output, **options):
            assert options['reference_text'] == ''
            return {'backend': 'voxcpm_native', 'model_family': 'voxcpm2', 'device': 'cuda'}
        def close(self): calls.append('closed')
    monkeypatch.setattr(native, 'NativeSession', Session)
    request = {'id': 'one', 'text': 'Bonjour.', 'reference_wav': str(tmp_path / 'ref.wav'),
               'output': str(tmp_path / 'out.wav'), 'steps': 8, 'language': 'fr'}
    output = io.StringIO()
    native.serve(tmp_path, 4, 'cuda', source=io.StringIO(json.dumps(request)),
                 protocol=output, errors=io.StringIO(), family='voxcpm2')
    response = json.loads(output.getvalue())
    assert response['ok'] and response['execution']['backend'] == 'voxcpm_native'
    assert calls == [('voxcpm2', 'cuda'), 'closed']


class InitializationLibrary(FakeLibrary):
    def __init__(self):
        super().__init__(np.sin(np.arange(4800) * .03) * .1)
        self.session_options = {}
    def audiocpp_abi_version(self): return 0x000200
    def audiocpp_build_version(self): return b'fake-abi-test'
    def audiocpp_registry_create(self, configuration, output):
        output._obj.value = 1
        return 0
    def audiocpp_model_load(self, registry, filename, configuration, options, output):
        self.model_family = configuration._obj.family_hint.decode()
        output._obj.value = 2
        return 0
    def audiocpp_options_create(self): return C.c_void_p(3)
    def audiocpp_options_set(self, options, name, value):
        self.session_options[name.decode()] = value.decode()
        return 0
    def audiocpp_options_free(self, options): pass
    def audiocpp_session_create(self, model, task, mode, configuration, options, output):
        self.selected_device = configuration._obj.backend.decode()
        output._obj.value = 4
        return 0
    def audiocpp_session_free(self, value): self.freed.append('session')
    def audiocpp_model_free(self, value): self.freed.append('model')
    def audiocpp_registry_free(self, value): self.freed.append('registry')


@pytest.mark.parametrize('device,performance', [('cpu', 'off'), ('cuda', 'off'), ('cuda', 'cuda_perf')])
def test_constructor_binds_same_model_family_and_explicit_session_performance(prepared, monkeypatch, device, performance):
    data, _, _ = prepared
    library = InitializationLibrary()
    monkeypatch.setattr(native.C, 'CDLL', lambda path: library)
    monkeypatch.setattr(native, '_bind', lambda value: value)
    session = native.NativeSession(data, device=device, family='voxcpm2', native_performance=performance)
    try:
        assert library.model_family == 'voxcpm2' and library.selected_device == device
        assert library.session_options == {'voxcpm2.mem_saver': 'false',
                                           'voxcpm2.prompt_cache_slots': '4',
                                           'voxcpm2.perf_mode': performance}
        assert session.info['backend'] == 'voxcpm_native'
        assert session.info['native_performance'] == performance
        assert session.info['native_source_revision'] == models.NATIVE_REVISION
    finally:
        session.close()
    assert library.freed == ['session', 'model', 'registry']


@pytest.mark.parametrize('family,device', [('voxcpm2', 'cpu'), ('omnivoice', 'cpu'), ('omnivoice', 'cuda')])
def test_cuda_optimization_is_never_applied_to_cpu_or_another_model(family, device):
    with pytest.raises(ValueError, match='VoxCPM2 native'):
        backend.validate_native_performance('cuda_perf', device, family)


def test_changing_session_optimization_recreates_model_but_changing_text_does_not(prepared, monkeypatch):
    data, _, _ = prepared
    created = []
    class Client:
        def __init__(self, library, model, directory, threads, device, key, record):
            self.key, self.performance, self.closed = key, record['native_performance'], False
            self.process, self.execution = SimpleNamespace(poll=lambda: None), {}
            created.append(self)
        def synthesize(self, *args): pass
        def close(self): self.closed = True
    monkeypatch.setattr(backend, '_BackendClient', Client)
    monkeypatch.setattr(backend, '_client', None)
    reference = data / 'reference.wav'
    reference.write_bytes(b'synthetic fixture')
    standard = backend.create_synthesizer(reference, data, family='voxcpm2', device='cuda')
    fast = backend.create_synthesizer(reference, data, family='voxcpm2', device='cuda', native_performance='cuda_perf')
    try:
        standard('First.', data / 'one.wav')
        fast('Second.', data / 'two.wav')
        fast('Third.', data / 'three.wav')
        assert len(created) == 2 and created[0].closed
        standard('Fourth.', data / 'four.wav')
        assert len(created) == 3 and created[1].closed
        assert [client.performance for client in created] == ['off', 'cuda_perf', 'off']
    finally:
        backend.close_backends()


def test_client_requires_actual_performance_mode_in_response():
    client = backend._BackendClient.__new__(backend._BackendClient)
    client.family, client.backend, client.device = 'voxcpm2', 'voxcpm_native', 'cuda'
    client.native_performance, client.execution = 'cuda_perf', {}
    report = {'backend': 'voxcpm_native', 'model_family': 'voxcpm2', 'device': 'cuda', 'native_performance': 'off'}
    with pytest.raises(ValueError, match='thiết bị'):
        client._execution(report)
    report.update(native_performance='cuda_perf', private_reference='/private/sample.wav')
    client._execution(report)
    assert client.execution['native_performance'] == 'cuda_perf'
    assert 'private_reference' not in client.execution
