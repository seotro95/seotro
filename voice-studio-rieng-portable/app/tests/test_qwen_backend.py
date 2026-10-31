"""Qwen runtime isolation, model integrity and local preset/clone contracts."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
from types import SimpleNamespace
from unittest import mock
import uuid

import numpy as np
import pytest
import soundfile as sf

import qwen_backend as backend


def write_model(data, engine):
    repository, folder = backend.MODELS[engine]
    directory = data / 'models' / folder
    entries = []
    for name in ('config.json', 'generation_config.json', 'tokenizer_config.json',
                 'model.safetensors', 'speech_tokenizer/config.json',
                 'speech_tokenizer/preprocessor_config.json', 'speech_tokenizer/model.safetensors',
                 'vocab.json', 'merges.txt'):
        payload = b'{}' if name.endswith('.json') else ('Fixture ' + name).encode()
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        entries.append({'name': name, 'size': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
    record = {'schema': 1, 'backend': 'qwen-isolated', 'engine': engine,
              'repository': repository, 'revision': 'a' * 40, 'model_dir': folder, 'files': entries}
    (data / 'models' / (engine + '.ready')).write_text(json.dumps(record), encoding='utf-8')
    return directory, record


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    data = tmp_path / 'data'
    write_model(data, 'qwen')
    write_model(data, 'qwen_clone')
    runtime = tmp_path / 'runtime-qwen'
    runtime.mkdir()
    executable = runtime / 'python.exe'
    executable.write_bytes(b'fixture interpreter, never executed')
    packages = runtime / 'Lib/site-packages'
    packages.mkdir(parents=True)
    for name, version in backend.RUNTIME_PACKAGES.items():
        metadata = packages / (name.replace('-', '_') + '-' + version + '.dist-info')
        metadata.mkdir()
        (metadata / 'METADATA').write_text(f'Name: {name}\nVersion: {version}\n', encoding='utf-8')
    monkeypatch.setenv('VOICE_STUDIO_QWEN_PYTHON', str(executable))
    monkeypatch.setattr(backend, '_runtime_cache', None)
    monkeypatch.setattr(backend, '_client', None)
    monkeypatch.setattr(backend, '_verified_models', set())
    yield data, runtime, packages
    backend.close_backends()


def test_importing_adapter_does_not_import_any_heavy_runtime():
    script = ('import sys;sys.path.insert(0,sys.argv[1]);import qwen_backend;'
              'assert not any(name in sys.modules for name in ("torch","transformers","qwen_tts"))')
    subprocess.run([sys.executable, '-s', '-c', script, str(Path(backend.__file__).parent)],
                   check=True, timeout=30)


def test_readiness_uses_separate_runtime_and_checksum_verification_is_mandatory_on_load(prepared):
    data, runtime, _ = prepared
    assert backend.runtime_ready() and backend.is_ready(data, 'qwen') and backend.is_ready(data, 'qwen_clone')
    model, _ = backend.prepared_model(data, 'qwen', verify=True)
    path = model / 'model.safetensors'
    original = path.read_bytes()
    path.write_bytes(original[:-1] + b'!')
    assert backend.is_ready(data, 'qwen'), 'Cheap readiness is not a full-file hash check'
    with pytest.raises(ValueError, match='SHA256'):
        backend.prepared_model(data, 'qwen', verify=True)
    (runtime / 'python.exe').unlink()
    assert not backend.is_ready(data, 'qwen')


@pytest.mark.parametrize('package', list(backend.RUNTIME_PACKAGES))
def test_wrong_isolated_package_version_is_not_ready(prepared, package):
    data, _, packages = prepared
    metadata = next(packages.glob(package.replace('-', '_') + '-*.dist-info')) / 'METADATA'
    metadata.write_text(f'Name: {package}\nVersion: 0.0.0\n', encoding='utf-8')
    assert not backend.runtime_ready() and not backend.is_ready(data)


def test_duplicate_isolated_packages_are_not_ready(prepared):
    _, _, packages = prepared
    duplicate = packages / 'qwen_tts-duplicate.dist-info'
    duplicate.mkdir()
    (duplicate / 'METADATA').write_text('Name: qwen-tts\nVersion: 0.1.1\n')
    assert not backend.runtime_ready()


@pytest.mark.parametrize(('field', 'value'), [
    ('schema', True), ('backend', 'other'), ('engine', 'qwen_clone'),
    ('repository', 'other/model'), ('revision', 'main'), ('model_dir', '../escape')])
def test_model_marker_cannot_select_another_source_or_path(prepared, field, value):
    data, _, _ = prepared
    marker = data / 'models/qwen.ready'
    record = json.loads(marker.read_text())
    record[field] = value
    marker.write_text(json.dumps(record))
    assert not backend.is_ready(data)


def test_missing_tokenizer_or_safetensor_shard_prevents_readiness(prepared):
    data, _, _ = prepared
    model, _ = backend.prepared_model(data)
    (model / 'speech_tokenizer/model.safetensors').unlink()
    assert not backend.is_ready(data)


@pytest.mark.parametrize('missing', ['generation_config.json', 'tokenizer_config.json',
                                    'speech_tokenizer/preprocessor_config.json'])
def test_sdk_required_generation_and_processor_configurations_are_mandatory(prepared, missing):
    data, _, _ = prepared
    model, _ = backend.prepared_model(data)
    marker = data / 'models/qwen.ready'
    record = json.loads(marker.read_text())
    record['files'] = [entry for entry in record['files'] if entry['name'] != missing]
    marker.write_text(json.dumps(record))
    (model / missing).unlink()
    assert not backend.is_ready(data)


def test_complete_fast_tokenizer_json_is_an_alternative_to_vocab_and_merges(prepared):
    data, _, _ = prepared
    model, _ = backend.prepared_model(data)
    marker = data / 'models/qwen.ready'
    record = json.loads(marker.read_text())
    record['files'] = [entry for entry in record['files'] if entry['name'] not in {'vocab.json', 'merges.txt'}]
    payload = b'{}'
    (model / 'tokenizer.json').write_bytes(payload)
    record['files'].append({'name': 'tokenizer.json', 'size': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
    marker.write_text(json.dumps(record))
    assert backend.prepared_model(data, verify=True)[0] == model


def test_reference_and_language_changes_keep_one_model_until_engine_switch(prepared, monkeypatch, tmp_path):
    data, _, _ = prepared
    created, requests = [], []
    class Client:
        def __init__(self, directory, engine, threads, key):
            self.key, self.engine, self.closed = key, engine, False
            self.process = SimpleNamespace(poll=lambda: None)
            created.append(self)
        def synthesize(self, text, output, **options):
            requests.append((self.engine, text, output, options))
        def close(self):
            self.closed = True
    monkeypatch.setattr(backend, '_BackendClient', Client)
    reference = tmp_path / 'private.wav'
    reference.write_bytes(b'Only dispatch is tested here')
    ryan = backend.create_synthesizer(data, speaker='Ryan')
    aiden = backend.create_synthesizer(data, speaker='Aiden', language='fr')
    clone = backend.create_synthesizer(data, engine='qwen_clone', language='fr',
                                       reference_audio=reference, reference_text='Original local reference.')
    ryan('First', data / 'first.wav')
    aiden('Deuxième', data / 'second.wav')
    ryan('Third', data / 'third.wav')
    assert len(created) == 1
    clone('Quatrième', data / 'fourth.wav')
    assert len(created) == 2 and created[0].closed
    assert requests[1][3]['speaker'] == 'Aiden' and requests[1][3]['language'] == 'fr'
    assert requests[3][3]['reference_wav'] == str(reference)
    assert requests[3][3]['reference_text'] == 'Original local reference.'


def test_gpu_request_is_rejected_explicitly_instead_of_changing_precision(prepared):
    data, _, _ = prepared
    with pytest.raises(ValueError, match='CPU FP32'):
        backend.create_synthesizer(data, speaker='Ryan', device='cuda')


@pytest.fixture
def fake_qwen(prepared, monkeypatch):
    observed = {'loads': [], 'custom': [], 'clone': [], 'prompts': []}
    class Model:
        @classmethod
        def from_pretrained(cls, path, **options):
            print('Fake upstream loading progress')
            observed['loads'].append((path, options))
            return cls()
        def generate_custom_voice(self, **options):
            observed['custom'].append(options)
            return [np.full(1200, .1, dtype=np.float32)], 24000
        def create_voice_clone_prompt(self, **options):
            observed['prompts'].append(options)
            return {'fixture_prompt': len(observed['prompts'])}
        def generate_voice_clone(self, **options):
            observed['clone'].append(options)
            return [np.full(1200, .2, dtype=np.float32)], 24000
    torch = SimpleNamespace(float32=object(), set_num_threads=lambda value: observed.update(threads=value),
                            inference_mode=contextlib.nullcontext)
    monkeypatch.setitem(sys.modules, 'torch', torch)
    monkeypatch.setitem(sys.modules, 'qwen_tts', SimpleNamespace(Qwen3TTSModel=Model))
    monkeypatch.setattr(backend.importlib.metadata, 'version', lambda package: backend.RUNTIME_PACKAGES[package])
    return observed, torch


def request(data, **options):
    return {'id': uuid.uuid4().hex, 'text': 'Hello.', 'language': 'en-US', 'speaker': 'Ryan',
            'quality': 'standard', 'reference_text': '',
            'output': str(data / 'audio' / (uuid.uuid4().hex + '.wav')), **options}


def test_all_nine_preset_speakers_use_local_cpu_fp32_and_pcm16(prepared, fake_qwen):
    data, _, _ = prepared
    observed, torch = fake_qwen
    session = backend._Session(data, 'qwen', 4)
    try:
        for speaker in sorted(backend.SPEAKERS):
            job = request(data, speaker=speaker, quality='fast')
            execution = session.synthesize(job)
            audio = sf.info(job['output'])
            assert audio.samplerate == 24000 and audio.channels == 1 and audio.subtype == 'PCM_16'
            assert execution['device'] == 'cpu' and execution['precision'] == 'fp32'
        assert len(observed['loads']) == 1 and len(observed['custom']) == 9
        options = observed['loads'][0][1]
        assert options == {'device_map': 'cpu', 'dtype': torch.float32,
                           'attn_implementation': 'sdpa', 'local_files_only': True}
        assert {value['speaker'] for value in observed['custom']} == backend.SPEAKERS
        assert all(v['do_sample'] is False and v['subtalker_dosample'] is False for v in observed['custom'])
    finally:
        session.close()


def test_clone_prompt_cache_preserves_reference_and_supplied_transcript(prepared, fake_qwen, tmp_path):
    data, _, _ = prepared
    observed, _ = fake_qwen
    reference = tmp_path / 'private-reference.wav'
    sf.write(reference, np.full(72000, .1, dtype=np.float32), 24000, subtype='PCM_16')
    original = reference.read_bytes()
    session = backend._Session(data, 'qwen_clone', 2)
    try:
        for _ in range(2):
            session.synthesize(request(data, reference_wav=str(reference), speaker=None))
        assert len(observed['prompts']) == 1
        assert observed['prompts'][0] == {'ref_audio': str(reference), 'ref_text': None, 'x_vector_only_mode': True}
        session.synthesize(request(data, reference_wav=str(reference), speaker=None,
                                   reference_text='Exact words supplied locally.'))
        assert len(observed['prompts']) == 2 and len(observed['clone']) == 3
        assert observed['prompts'][1]['ref_text'] == 'Exact words supplied locally.'
        assert observed['prompts'][1]['x_vector_only_mode'] is False
        assert reference.read_bytes() == original
    finally:
        session.close()


def test_clone_rejects_silent_reference_before_enrolling(prepared, fake_qwen, tmp_path):
    data, _, _ = prepared
    reference = tmp_path / 'silence.wav'
    sf.write(reference, np.zeros(72000, dtype=np.float32), 24000)
    session = backend._Session(data, 'qwen_clone', 2)
    try:
        with pytest.raises(ValueError, match='Mẫu Qwen'):
            session.synthesize(request(data, reference_wav=str(reference), speaker=None))
        assert not fake_qwen[0]['prompts']
    finally:
        session.close()


def test_stdio_keeps_one_model_and_never_writes_upstream_logs_to_protocol(prepared, fake_qwen):
    data, _, _ = prepared
    jobs = [request(data), request(data, speaker='Aiden', language='fr')]
    source = io.StringIO(''.join(json.dumps(job) + '\n' for job in jobs))
    protocol, errors = io.StringIO(), io.StringIO()
    backend.serve(data, 'qwen', 4, source=source, protocol=protocol, errors=errors)
    responses = [json.loads(line) for line in protocol.getvalue().splitlines()]
    assert len(responses) == 2 and all(value['ok'] for value in responses)
    assert len(fake_qwen[0]['loads']) == 1
    assert 'Fake upstream loading progress' in errors.getvalue()
    assert all(value['execution']['device'] == 'cpu' for value in responses)


def test_stdio_rejects_output_outside_app_data_before_loading_model(prepared, monkeypatch, tmp_path):
    data, _, _ = prepared
    monkeypatch.setattr(backend, '_Session', lambda *args: pytest.fail('Do not load a model for an invalid output path'))
    job = request(data, output=str(tmp_path / 'outside.wav'))
    protocol = io.StringIO()
    backend.serve(data, 'qwen', 4, source=io.StringIO(json.dumps(job) + '\n'), protocol=protocol, errors=io.StringIO())
    assert json.loads(protocol.getvalue())['ok'] is False
    assert not (tmp_path / 'outside.wav').exists()


def test_stdio_preserves_the_actual_bounded_model_loading_error(prepared, monkeypatch):
    data, _, _ = prepared
    actual = 'missing processor dependency\n' + 'x' * 1000
    def fail(*args):
        raise ValueError(actual)
    monkeypatch.setattr(backend, '_Session', fail)
    job = request(data)
    protocol = io.StringIO()
    backend.serve(data, 'qwen', 4, source=io.StringIO(json.dumps(job) + '\n'),
                  protocol=protocol, errors=io.StringIO())
    result = json.loads(protocol.getvalue())
    assert result['ok'] is False and result['id'] == job['id'] and result['output'] == job['output']
    assert result['error'].startswith('ValueError: missing processor dependency ')
    assert len(result['error']) == 600 and '\n' not in result['error']


def test_client_reports_bound_child_error_and_closes_the_failed_process(prepared, monkeypatch):
    data, _, _ = prepared
    ident = 'a' * 32
    monkeypatch.setattr(backend.uuid, 'uuid4', lambda: SimpleNamespace(hex=ident))
    client = backend._BackendClient.__new__(backend._BackendClient)
    client.process = SimpleNamespace(stdin=io.StringIO())
    client.responses = queue.Queue()
    client.responses.put(json.dumps({'ok': False, 'id': ident, 'output': str(data / 'out.wav'),
                                     'error': 'ImportError: actual missing runtime dependency'}))
    client.close = mock.Mock()
    with pytest.raises(ValueError, match='ImportError: actual missing runtime dependency'):
        client.synthesize('Hello.', data / 'out.wav')
    client.close.assert_called_once()


def test_main_redirects_descriptor_one_logs_without_corrupting_stdio_protocol(tmp_path):
    script = '''
import json,os,sys
sys.path.insert(0,sys.argv[1])
import qwen_backend as backend
def fake_serve(data,engine,threads,protocol=None):
    os.write(1,b'C dependency stdout message\\n')
    print('Python dependency stdout message',flush=True)
    protocol.write(json.dumps({'ok':True,'device':'cpu'})+'\\n')
    protocol.flush()
backend.serve=fake_serve
backend.main(['--serve','--data-dir',sys.argv[2],'--engine','qwen'])
'''
    result = subprocess.run([sys.executable, '-s', '-X', 'utf8', '-c', script,
                             str(Path(backend.__file__).parent), str(tmp_path)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding='utf-8', check=True, timeout=30)
    assert json.loads(result.stdout) == {'ok': True, 'device': 'cpu'}
    assert 'C dependency stdout message' in result.stderr
    assert 'Python dependency stdout message' in result.stderr


def test_child_environment_is_offline_and_cannot_inherit_main_python_packages(prepared, monkeypatch):
    data, _, _ = prepared
    monkeypatch.setenv('PYTHONPATH', 'must-not-enter-isolated-runtime')
    monkeypatch.setenv('PYTHONHOME', 'must-not-enter-isolated-runtime')
    env = backend._environment(data, 4)
    assert 'PYTHONPATH' not in env and 'PYTHONHOME' not in env
    assert env['HF_HUB_OFFLINE'] == env['TRANSFORMERS_OFFLINE'] == '1'
    assert env['CUDA_VISIBLE_DEVICES'] == '' and env['TOKENIZERS_PARALLELISM'] == 'false'


def test_worker_dispatches_both_qwen_engines_without_importing_torch_or_hf(tmp_path):
    script = '''
import builtins,json,os,pathlib,sys,types
sys.path.insert(0,sys.argv[1])
os.environ['VOICE_STUDIO_DATA_DIR']=sys.argv[2]
original_import=builtins.__import__
def isolated_import(name,*args,**kwargs):
    if name.split('.')[0] in {'torch','qwen_tts','huggingface_hub'}:
        raise AssertionError('Heavy dependency imported in main worker: '+name)
    return original_import(name,*args,**kwargs)
builtins.__import__=isolated_import
calls=[]
def create(data,**options):
    calls.append((str(data),options))
    return lambda text,output:None
sys.modules['qwen_backend']=types.SimpleNamespace(create_synthesizer=create)
import worker,voice_library
voice_library.resolve_reference=lambda *args:(pathlib.Path(sys.argv[3]),{'transcript':'Original local sample.'})
for engine in ('qwen','qwen_clone'):
    worker.load_synthesizer({'engine':engine,'speaker':'Aiden','voice_id':'test',
                            'language':'fr','nano_threads':2,'quality':'standard'})
assert len(calls)==2
assert calls[0][1]['speaker']=='Aiden' and calls[0][1]['device']=='cpu'
assert calls[1][1]['reference_text']=='Original local sample.'
assert str(calls[1][1]['reference_audio'])==sys.argv[3]
assert not any(name in sys.modules for name in ('torch','qwen_tts','huggingface_hub'))
'''
    subprocess.run([sys.executable, '-s', '-X', 'utf8', '-c', script,
                    str(Path(backend.__file__).parent), str(tmp_path / 'data'), str(tmp_path / 'reference.wav')],
                   check=True, timeout=30)
