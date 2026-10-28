"""International adapter boundaries, using fixtures rather than real voices."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import wave

import pytest
import voxcpm_backend as backend


def test_runtime_override_keeps_virtual_environment_executable(tmp_path, monkeypatch):
    base = tmp_path/'base-python'
    base.touch()
    virtual = tmp_path/'venv'/'bin'/'python'
    virtual.parent.mkdir(parents=True)
    virtual.symlink_to(base)
    monkeypatch.setenv('VOICE_STUDIO_INTERNATIONAL_PYTHON', str(virtual))
    assert backend.runtime_python() == virtual.absolute()


def source_pack(tmp_path):
    source = tmp_path/'voxcpm2-original'
    source.mkdir()
    files = {'config.json': json.dumps({'architecture': 'voxcpm2', 'dtype': 'bfloat16', 'device': 'cuda'}).encode(),
             'model.safetensors': b'model fixture', 'audiovae.safetensors': b'vae fixture', 'tokenizer.json': b'{}'}
    entries = []
    for name, content in files.items():
        (source/name).write_bytes(content)
        entries.append({'name': name, 'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)})
    (source/'MODEL_PROVENANCE.json').write_text(json.dumps({
        'repository': 'openbmb/VoxCPM2', 'revision': 'a'*40, 'license': 'apache-2.0', 'files': entries}))
    return source


@pytest.mark.parametrize('good_probe', [True, False])
def test_cpu_copy_preserves_original_and_readiness_requires_synthesis(tmp_path, monkeypatch, good_probe):
    source = source_pack(tmp_path)
    data = tmp_path/'data'
    monkeypatch.setattr(backend, '_load_model', lambda path, threads: object())
    def generate(model, text, reference, output):
        assert '\u0e2a' in text and reference is None
        assert not (data/'models/voxcpm.ready').exists()
        if not good_probe:
            raise ValueError('synthetic probe failed')
        with wave.open(str(output), 'wb') as target:
            target.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
            target.writeframes(b'\0\x10'*4800)
        return 4800
    monkeypatch.setattr(backend, '_generate', generate)
    if good_probe:
        backend.prepare_model(data, model_source=source)
        prepared = backend.prepared_model(data)
        assert json.loads((prepared/'config.json').read_text())['dtype'] == 'float32'
        assert (data/'models/voxcpm.ready').exists()
    else:
        with pytest.raises(ValueError, match='probe failed'):
            backend.prepare_model(data, model_source=source)
        assert not (data/'models/voxcpm.ready').exists()
    assert json.loads((source/'config.json').read_text())['dtype'] == 'bfloat16'
    assert (source/'model.safetensors').read_bytes() == b'model fixture'


def test_bad_offline_model_hash_is_rejected(tmp_path):
    source = source_pack(tmp_path)
    (source/'model.safetensors').write_bytes(b'wrong weights')
    with pytest.raises(ValueError, match='model'):
        backend._source_model(tmp_path/'data', source)


def test_voice_switch_keeps_one_backend_and_correct_reference(tmp_path, monkeypatch):
    created = []
    calls = []
    class Client:
        def __init__(self, data, threads):
            self.key = (str(backend.runtime_python()), str(data), threads)
            self.process = SimpleNamespace(poll=lambda: None)
            self.closed = False
            created.append(self)
        def synthesize(self, text, reference, output, steps=10):
            calls.append((text, reference.name, steps))
        def close(self):
            self.closed = True
    monkeypatch.setattr(backend, '_client', None)
    monkeypatch.setattr(backend, '_BackendClient', Client)
    refs = [tmp_path/'first.wav', tmp_path/'second.wav']
    for path in refs:path.write_bytes(b'reference fixture')
    first = backend.create_synthesizer(refs[0], tmp_path, 4, steps=10)
    second = backend.create_synthesizer(refs[1], tmp_path, 4, steps=4)
    balanced = backend.create_synthesizer(refs[1], tmp_path, 4, steps=8)
    try:
        first('first', tmp_path/'a.wav')
        second('second', tmp_path/'b.wav')
        balanced('balanced', tmp_path/'d.wav')
        first('first again', tmp_path/'c.wav')
        assert len(created) == 1
        assert calls == [('first', 'first.wav', 10), ('second', 'second.wav', 4),
                         ('balanced', 'second.wav', 8), ('first again', 'first.wav', 10)]
    finally:
        backend.close_backends()
    assert created[0].closed


def test_child_stdout_contains_only_json_responses(tmp_path, monkeypatch):
    data = tmp_path/'data';(data/'parts').mkdir(parents=True)
    reference = tmp_path/'ref.wav';reference.write_bytes(b'reference fixture')
    requests = [{'id': str(index), 'text': 'sample', 'reference_wav': str(reference),
                 'output': str(data/'parts'/f'{index}.wav'), **settings}
                for index, settings in enumerate(({'steps': 4}, {'steps': 8}, {}), 1)]
    monkeypatch.setattr(backend, 'prepared_model', lambda data: tmp_path)
    monkeypatch.setattr(backend, '_load_model', lambda path, threads: object())
    received_steps = []
    def generate(model, text, reference, output, steps=10):
        received_steps.append(steps)
        print('upstream progress text')
        output.write_bytes(b'output fixture')
        return 24000
    monkeypatch.setattr(backend, '_generate', generate)
    monkeypatch.setattr(backend.sys, 'argv', ['backend', '--serve', '--data-dir', str(data)])
    monkeypatch.setattr(backend.sys, 'stdin', io.StringIO('\n'.join(map(json.dumps, requests))+'\n'))
    output, errors = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
        backend.main()
    responses = [json.loads(line) for line in output.getvalue().splitlines()]
    assert [entry['id'] for entry in responses] == ['1', '2', '3']
    assert received_steps == [4, 8, 10]
    assert all(entry['ok'] and entry['sample_rate'] == 24000 for entry in responses)
    assert 'upstream progress text' in errors.getvalue()
    assert 'upstream progress text' not in output.getvalue()


@pytest.mark.parametrize('steps', [0, 3, 5, 9, 11, 4.0, '4', True, None])
def test_invalid_steps_are_rejected_before_loading_a_backend(tmp_path, monkeypatch, steps):
    reference = tmp_path/'reference.wav';reference.write_bytes(b'reference fixture')
    def unexpected_client(*args, **kwargs):
        pytest.fail('invalid settings must never start an international model')
    monkeypatch.setattr(backend, '_BackendClient', unexpected_client)
    with pytest.raises(ValueError, match='4, 8'):
        backend.create_synthesizer(reference, tmp_path, steps=steps)


@pytest.mark.parametrize('steps', [4, 8, 10])
def test_generation_preserves_reference_and_requested_steps(tmp_path, steps):
    import numpy as np
    import soundfile as sf
    calls = []
    class Model:
        tts_model = SimpleNamespace(sample_rate=48000)
        def generate(self, **settings):
            calls.append(settings)
            return np.sin(np.arange(4800, dtype=np.float32)/10)*0.1
    reference = tmp_path/'reference.wav'
    destination = tmp_path/'parts'/'speech.wav'
    frames = backend._generate(Model(), 'Read this sentence.', reference, destination, steps=steps)
    assert calls == [{'text': 'Read this sentence.', 'reference_wav_path': str(reference),
                      'cfg_value': 2.0, 'inference_timesteps': steps,
                      'normalize': False, 'denoise': False, 'retry_badcase': True}]
    samples, rate = sf.read(destination)
    assert frames == len(samples) == 2400 and rate == 24000
    assert np.max(np.abs(samples)) > 0.01


@pytest.mark.parametrize('steps', [3, 9, 10.0, '8', True, None])
def test_generation_rejects_unsupported_steps_without_running_model(tmp_path, steps):
    model = SimpleNamespace(generate=lambda **kwargs: pytest.fail('invalid step count reached model'))
    with pytest.raises(ValueError, match='bước'):
        backend._generate(model, 'Sample.', None, tmp_path/'out.wav', steps=steps)
