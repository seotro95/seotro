"""Native integration invariants without downloading a model or private voice."""
import contextlib
import ctypes as C
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf

import fast_multilingual as backend
import native_synthesis as native


@pytest.fixture
def installed(tmp_path, monkeypatch):
    data = tmp_path/'data'
    model = data/'models/omnivoice'/backend.MODEL_NAME
    model.parent.mkdir(parents=True)
    payload = b'GGUFmodel-fixture-not-real-weights'
    model.write_bytes(payload)
    record = {'schema': 1, 'backend': 'omnivoice', 'model_dir': 'omnivoice',
              'filename': backend.MODEL_NAME, 'size': len(payload),
              'sha256': hashlib.sha256(payload).hexdigest(),
              'repository': backend.MODEL_REPOSITORY, 'revision': 'a'*40,
              'license': 'CC-BY-NC-4.0'}
    (data/'models/omnivoice.ready').write_text(json.dumps(record))
    root = tmp_path/'runtime-native'
    monkeypatch.setenv('VOICE_STUDIO_NATIVE_ROOT', str(root))
    for device in ('cpu', 'cuda'):
        name = 'audiocpp.dll' if sys.platform == 'win32' else ('libaudiocpp.dylib' if sys.platform == 'darwin' else 'libaudiocpp.so')
        library = root/device/name
        library.parent.mkdir(parents=True)
        library.write_bytes(b'library-fixture')
    return data, model, record


def test_readiness_and_full_checksum_are_distinct(installed):
    data, model, _ = installed
    assert backend.is_ready(data) and backend.cuda_available(data)
    assert backend.prepared_model(data, verify=True)[0] == model
    # A damaged file of the same size can never be loaded merely because its
    # cheap readiness check passed.
    payload = model.read_bytes()
    model.write_bytes(payload[:-1]+b'!')
    assert backend.is_ready(data)
    with pytest.raises(ValueError, match='SHA256'):
        backend.prepared_model(data, verify=True)


@pytest.mark.parametrize('field,value', [('model_dir', '../elsewhere'), ('filename', '../model.gguf'),
                                        ('repository', 'other/repo'), ('revision', 'main'),
                                        ('schema', True), ('size', True)])
def test_malformed_model_marker_never_reports_ready(installed, field, value):
    data, _, record = installed
    record[field] = value
    (data/'models/omnivoice.ready').write_text(json.dumps(record))
    assert not backend.is_ready(data)
    assert not backend.cuda_available(data)


@pytest.mark.parametrize('record', [[], None, 'wrong', True, 123])
def test_non_object_model_marker_never_crashes_readiness(installed, record):
    data, _, _ = installed
    (data/'models/omnivoice.ready').write_text(json.dumps(record))
    assert not backend.is_ready(data)
    assert not backend.cuda_available(data)


def test_voice_language_and_steps_switch_reuses_exactly_one_model(installed, tmp_path, monkeypatch):
    data, _, _ = installed
    created, requests = [], []
    class Client:
        def __init__(self, library, model, data, threads, device, key, record):
            self.key = key
            self.process = SimpleNamespace(poll=lambda: None)
            self.execution = {'device': device}
            self.closed = False
            created.append(self)
        def synthesize(self, text, reference, output, steps, language, reference_text):
            requests.append((text, reference.name, steps, language, reference_text, self.key[-1]))
        def close(self):
            self.closed = True
    monkeypatch.setattr(backend, '_client', None)
    monkeypatch.setattr(backend, '_BackendClient', Client)
    refs = [tmp_path/'fr.wav', tmp_path/'ja.wav']
    for path in refs:
        path.write_bytes(b'synthetic reference fixture')
    french = backend.create_synthesizer(refs[0], data, steps=8, device='cpu', language='fr', reference_text='Bonjour.')
    japanese = backend.create_synthesizer(refs[1], data, steps=32, device='cpu', language='ja', reference_text='こんにちは。')
    gpu = backend.create_synthesizer(refs[0], data, steps=16, device='cuda', language='fr', reference_text='Bonjour.')
    try:
        french('Bonjour', data/'a.wav')
        japanese('こんにちは', data/'b.wav')
        french('Bonjour encore', data/'c.wav')
        assert len(created) == 1
        gpu('GPU request', data/'d.wav')
        assert len(created) == 2 and created[0].closed
        assert backend.execution_info() == {'device': 'cuda'}
        assert requests == [('Bonjour', 'fr.wav', 8, 'fr', 'Bonjour.', 'cpu'),
                            ('こんにちは', 'ja.wav', 32, 'ja', 'こんにちは。', 'cpu'),
                            ('Bonjour encore', 'fr.wav', 8, 'fr', 'Bonjour.', 'cpu'),
                            ('GPU request', 'fr.wav', 16, 'fr', 'Bonjour.', 'cuda')]
    finally:
        backend.close_backends()
    assert all(client.closed for client in created)


def test_uninstalled_cuda_is_rejected_without_cpu_fallback(installed, tmp_path):
    data, _, _ = installed
    backend.library_path('cuda').unlink()
    ref = tmp_path/'ref.wav'
    ref.write_bytes(b'fixture')
    assert backend.is_ready(data) and not backend.cuda_available(data)
    with pytest.raises(ValueError, match='CUDA'):
        backend.create_synthesizer(ref, data, device='cuda', reference_text='Valid transcript.')


def test_native_error_closes_failed_client_before_next_attempt(installed, tmp_path, monkeypatch):
    data, _, _ = installed
    created = []
    class Client:
        def __init__(self, library, model, data, threads, device, key, record):
            self.key = key
            self.process = SimpleNamespace(poll=lambda: None)
            self.closed = False
            self.execution = {}
            created.append(self)
        def synthesize(self, *args):
            if len(created) == 1:
                raise ValueError('CUDA initialization failed')
        def close(self):
            self.closed = True
    monkeypatch.setattr(backend, '_client', None)
    monkeypatch.setattr(backend, '_BackendClient', Client)
    reference = tmp_path/'ref.wav'
    reference.write_bytes(b'fixture')
    synth = backend.create_synthesizer(reference, data, device='cuda', reference_text='Valid transcript.')
    try:
        with pytest.raises(ValueError, match='CUDA initialization'):
            synth('text', data/'out.wav')
        assert created[0].closed and backend.execution_info() == {}
        synth('retry', data/'out.wav')
        assert len(created) == 2 and all(client.key[-1] == 'cuda' for client in created)
    finally:
        backend.close_backends()


def test_missing_transcript_uses_local_asr_once_and_refreshes_after_reference_change(installed, tmp_path, monkeypatch):
    data, _, _ = installed
    asr_calls, requests, created = [], [], []
    def transcribe(reference, directory, language):
        asr_calls.append((reference.read_bytes(), directory, language))
        return 'Local transcript ' + str(len(asr_calls))
    monkeypatch.setitem(sys.modules, 'native_transcript', SimpleNamespace(reference_transcript=transcribe))
    class Client:
        def __init__(self, library, model, data, threads, device, key, record):
            self.key = key
            self.process = SimpleNamespace(poll=lambda: None)
            self.execution = {'backend': 'omnivoice', 'device': device}
            created.append(self)
        def synthesize(self, text, reference, output, steps, language, reference_text):
            requests.append((reference.read_bytes(), reference_text))
        def close(self):
            pass
    monkeypatch.setattr(backend, '_client', None)
    monkeypatch.setattr(backend, '_BackendClient', Client)
    reference = tmp_path/'ref.wav'
    reference.write_bytes(b'original sample')
    synth = backend.create_synthesizer(reference, data, language='fr', reference_language='ja')
    try:
        synth('First', data/'first.wav')
        synth('Second', data/'second.wav')
        reference.write_bytes(b'replaced sample with another speaker')
        synth('Third', data/'third.wav')
        assert len(created) == 1 and len(asr_calls) == 2
        assert all(call[1:] == (data, 'ja') for call in asr_calls)
        assert requests == [(b'original sample', 'Local transcript 1'),
                            (b'original sample', 'Local transcript 1'),
                            (b'replaced sample with another speaker', 'Local transcript 2')]
        assert backend.execution_info() == {'backend': 'omnivoice', 'device': 'cpu'}
    finally:
        backend.close_backends()


class FakeLibrary:
    def __init__(self, waveform):
        self.audio = np.asarray(waveform, dtype=np.float32)
        self.options = {}
        self.freed = []
    def audiocpp_request_create(self): return C.c_void_p(11)
    def audiocpp_request_set_text(self, request, text, language):
        self.text, self.language = text.decode(), language.decode()
        return 0
    def audiocpp_request_set_voice_audio(self, request, samples, frames, rate, channels):
        self.reference = np.ctypeslib.as_array(samples, shape=(frames*channels,)).copy()
        return 0
    def audiocpp_request_set_option(self, request, key, value):
        self.options[key.decode()] = value.decode()
        return 0
    def audiocpp_session_run(self, session, request, result):
        result._obj.value = 12
        return 0
    def audiocpp_result_audio(self, result, samples, frames, rate, channels):
        C.cast(samples, C.POINTER(C.POINTER(C.c_float)))[0] = self.audio.ctypes.data_as(C.POINTER(C.c_float))
        frames._obj.value, rate._obj.value, channels._obj.value = len(self.audio), 48000, 1
        return 0
    def audiocpp_result_free(self, result): self.freed.append('result')
    def audiocpp_request_free(self, request): self.freed.append('request')


@pytest.mark.parametrize('language,model_language', [('fr', 'fr'), ('en-US', 'en'), ('ja', 'ja'), ('ko', 'ko'), ('th', 'th'),
                                                    ('ar', 'arb'), ('ne', 'npi'), ('tl', 'fil'), ('no', 'no')])
def test_c_abi_receives_exact_reference_language_transcript_and_steps(tmp_path, language, model_language):
    reference = tmp_path/'ref.wav'
    samples = np.sin(np.arange(24000)*0.02).astype(np.float32)*0.2
    sf.write(str(reference), samples, 24000, subtype='FLOAT')
    session = native.NativeSession.__new__(native.NativeSession)
    session.threads, session.device, session.session = 4, 'cuda', C.c_void_p(7)
    session.lib = FakeLibrary(np.sin(np.arange(4800)*0.03)*0.1)
    session.info = {'international_backend': 'omnivoice', 'device': 'cuda'}
    output = tmp_path/'speech.wav'
    info = session.synthesize('Original text', reference, output, steps=8, language=language, reference_text='Original transcript')
    assert session.lib.text == 'Original text' and session.lib.language == model_language
    assert np.array_equal(session.lib.reference, samples)
    assert session.lib.options == {'reference_text': 'Original transcript', 'num_inference_steps': '8', 'guidance_scale': '2.0'}
    assert info['device'] == 'cuda' and info['model_language'] == model_language and info['omnivoice_steps'] == 8
    details = sf.info(str(output))
    assert details.samplerate == 24000 and details.channels == 1 and details.frames == 2400
    assert session.lib.freed == ['result', 'request']


@pytest.mark.parametrize('waveform', [np.zeros(100), np.full(100, np.nan), np.full(100, np.inf)])
def test_invalid_native_audio_never_becomes_a_successful_output(tmp_path, waveform):
    reference = tmp_path/'ref.wav'
    sf.write(str(reference), np.sin(np.arange(2400)*0.1)*0.1, 24000)
    session = native.NativeSession.__new__(native.NativeSession)
    session.threads, session.device, session.session = 4, 'cpu', C.c_void_p(7)
    session.lib = FakeLibrary(waveform)
    session.info = {}
    output = tmp_path/'speech.wav'
    with pytest.raises(ValueError, match='tiếng hợp lệ'):
        session.synthesize('Original text', reference, output, reference_text='Valid transcript.')
    assert not output.exists() and session.lib.freed == ['result', 'request']


def test_protocol_reuses_session_and_restarts_after_failure(tmp_path, monkeypatch):
    instances = []
    class Session:
        def __init__(self, data, threads, device):
            self.closed = False
            instances.append(self)
        def synthesize(self, text, reference, output, **settings):
            print('native progress')
            if text == 'fail': raise RuntimeError('simulated CUDA failure')
            return {'device': 'cuda', 'international_backend': 'omnivoice', **settings}
        def close(self): self.closed = True
    monkeypatch.setattr(native, 'NativeSession', Session)
    requests = [{'id': str(i), 'text': text, 'reference_wav': str(tmp_path/'ref.wav'),
                 'output': str(tmp_path/f'{i}.wav'), 'steps': 16, 'language': 'fr', 'reference_text': ''}
                for i, text in enumerate(('first', 'second', 'fail', 'retry'))]
    source = io.StringIO('\n'.join(map(json.dumps, requests)))
    protocol, errors = io.StringIO(), io.StringIO()
    native.serve(tmp_path, 4, 'cuda', source, protocol, errors)
    responses = [json.loads(line) for line in protocol.getvalue().splitlines()]
    assert [item['ok'] for item in responses] == [True, True, False, True]
    assert len(instances) == 2 and all(instance.closed for instance in instances)
    assert 'native progress' in errors.getvalue() and 'simulated CUDA failure' in responses[2]['error']


def test_c_stdout_cannot_corrupt_child_protocol(tmp_path):
    # ctypes libraries can write to fd 1 directly, bypassing redirect_stdout.
    # Exercise the real daemon entry point in a child, without native weights.
    script = """
import json, os, sys
import native_synthesis as native
def serve(data, threads, device, protocol):
    os.write(1, b'native C progress\\n')
    print('native Python progress')
    protocol.write(json.dumps({'ok': True})+'\\n')
native.serve = serve
sys.argv = ['native_synthesis', '--serve', '--data-dir', sys.argv[1]]
native.main()
"""
    result = subprocess.run([sys.executable, '-c', script, str(tmp_path)],
                            cwd=Path(native.__file__).parent, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == {'ok': True}
    assert 'native C progress' in result.stderr and 'native Python progress' in result.stderr
