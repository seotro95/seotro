"""Lossless local reference preparation, cache recovery and worker isolation."""
from concurrent.futures import ThreadPoolExecutor
import importlib
import io
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
import zipfile

import numpy as np
import pytest

import turbo_reference as cache


class Model:
    def __init__(self, root):
        self.backend = 'onnx'
        self.backbone_repo = 'example/pinned-turbo'
        self.engine = SimpleNamespace(
            checkpoint_path=root / 'model', cfg={'n_vq': 16, 'speaker_embedding_dim': 192},
            _codec_enc_path=str(root / 'codec.onnx'),
            _resolve_root_file=lambda filename: str(root / filename))
        self.embedding = np.linspace(-.5, .5, 192, dtype=np.float32)
        self.codes = np.arange(25 * 16, dtype=np.int64).reshape(25, 16)
        self.calls = 0

    def encode_reference(self, reference, *, denoise):
        assert denoise is False
        self.calls += 1
        time.sleep(.01)
        return self.embedding.copy(), self.codes.copy()


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(cache.importlib.metadata, 'version', lambda package: '3.8.3')
    reference = tmp_path / 'private.wav'
    reference.write_bytes(b'public fixture reference bytes')
    for filename in ('codec.onnx', 'codec.data', 'speaker_encoder.onnx'):
        (tmp_path / filename).write_bytes(filename.encode())
    return Model(tmp_path), reference, tmp_path / 'data'


def test_restart_reuses_lossless_arrays_without_enrolling(prepared):
    model, reference, data = prepared
    first = cache.prepared_turbo_voice(model, reference, data)
    assert model.calls == 1
    assert np.array_equal(first['speaker_emb'], model.embedding)
    assert np.array_equal(first['codes'], model.codes)
    restarted = Model(reference.parent)
    second = cache.prepared_turbo_voice(restarted, reference, data)
    assert restarted.calls == 0
    assert np.array_equal(first['speaker_emb'], second['speaker_emb'])
    assert np.array_equal(first['codes'], second['codes'])
    assert second['speaker_emb'].dtype == np.float32 and second['codes'].dtype == np.int64
    assert len(list((data / 'cache' / 'turbo-references').glob('*.npz'))) == 1


@pytest.mark.parametrize('change', ['reference', 'codec', 'codec_data', 'speaker', 'precision', 'version'])
def test_changed_reference_or_encoder_invalidates_cache(prepared, monkeypatch, change):
    model, reference, data = prepared
    cache.prepared_turbo_voice(model, reference, data)
    precision = 'fp32'
    if change == 'reference':
        reference.write_bytes(b'a different selected speaker sample')
    elif change == 'precision':
        precision = 'int8'
    elif change == 'version':
        monkeypatch.setattr(cache.importlib.metadata, 'version', lambda package: '3.8.4')
    else:
        filename = {'codec': 'codec.onnx', 'codec_data': 'codec.data', 'speaker': 'speaker_encoder.onnx'}[change]
        (reference.parent / filename).write_bytes(b'a changed reference encoder model file')
    cache.prepared_turbo_voice(model, reference, data, precision=precision)
    assert model.calls == 2


@pytest.mark.parametrize('damage', ['truncated', 'pickle', 'bad_shape', 'schema', 'wrong_key', 'declared_huge'])
def test_bad_cache_is_rebuilt_from_original_sample(prepared, damage):
    model, reference, data = prepared
    expected = cache.prepared_turbo_voice(model, reference, data)
    path = next((data / 'cache' / 'turbo-references').glob('*.npz'))
    key = path.stem
    if damage == 'truncated':
        path.write_bytes(b'broken NPZ')
    elif damage == 'declared_huge':
        with zipfile.ZipFile(path, 'w') as archive:
            for name, array in {'schema': np.asarray(cache.SCHEMA), 'key': np.asarray(key),
                                'speaker_emb': expected['speaker_emb']}.items():
                buffer = io.BytesIO()
                np.save(buffer, array, allow_pickle=False)
                archive.writestr(name + '.npy', buffer.getvalue())
            buffer = io.BytesIO()
            np.lib.format.write_array_header_1_0(buffer, {'descr': '<i8', 'fortran_order': False,
                                                        'shape': (10 ** 12, 16)})
            archive.writestr('codes.npy', buffer.getvalue())
    else:
        arrays = {'schema': np.asarray(cache.SCHEMA), 'key': np.asarray(key), **expected}
        if damage == 'pickle':
            arrays['codes'] = np.asarray([object()], dtype=object)
        elif damage == 'bad_shape':
            arrays['codes'] = np.zeros((4, 7), dtype=np.int64)
        elif damage == 'schema':
            arrays['schema'] = np.asarray(999)
        elif damage == 'wrong_key':
            arrays['key'] = np.asarray('a different voice cache')
        np.savez(path, **arrays)
    recovered = cache.prepared_turbo_voice(model, reference, data)
    assert model.calls == 2
    assert np.array_equal(recovered['speaker_emb'], expected['speaker_emb'])
    assert np.array_equal(recovered['codes'], expected['codes'])


def test_concurrent_workers_encode_once(prepared):
    model, reference, data = prepared
    models = [Model(reference.parent) for _ in range(4)]
    with ThreadPoolExecutor(4) as pool:
        outputs = list(pool.map(lambda item: cache.prepared_turbo_voice(item, reference, data), models))
    assert sum(item.calls for item in models) == 1
    assert all(np.array_equal(output['codes'], model.codes) for output in outputs)
    assert not list((data / 'cache' / 'turbo-references').glob('.turbo-reference-*'))


def test_missing_original_sample_never_uses_stale_voice(prepared):
    model, reference, data = prepared
    cache.prepared_turbo_voice(model, reference, data)
    reference.unlink()
    with pytest.raises(FileNotFoundError):
        cache.prepared_turbo_voice(model, reference, data)
    assert model.calls == 1


def test_failed_encoder_leaves_no_cache_and_can_retry(prepared, monkeypatch):
    model, reference, data = prepared
    original = model.encode_reference
    def fail(*args, **kwargs):
        raise ValueError('invalid selected reference')
    monkeypatch.setattr(model, 'encode_reference', fail)
    with pytest.raises(ValueError, match='invalid selected reference'):
        cache.prepared_turbo_voice(model, reference, data)
    assert not list((data / 'cache' / 'turbo-references').glob('*.npz'))
    monkeypatch.setattr(model, 'encode_reference', original)
    cache.prepared_turbo_voice(model, reference, data)
    assert model.calls == 1


def test_crashed_process_releases_reference_lock(tmp_path):
    path = tmp_path / 'cache.lock'
    script = "from pathlib import Path; from turbo_reference import _exclusive; import os,sys\nwith _exclusive(Path(sys.argv[1]),None): os._exit(0)\n"
    environment = {**os.environ, 'PYTHONPATH': str(Path(cache.__file__).parent)}
    subprocess.run([sys.executable, '-c', script, str(path)], env=environment, check=True, timeout=15)
    # The zero-length file is retained; the dead owner's OS lock is released.
    assert path.exists()
    with cache._exclusive(path, None):
        pass


def test_cancelled_reference_wait_does_not_encode(prepared):
    model, reference, data = prepared
    cancelled = reference.parent / 'cancel.flag'
    cancelled.touch()
    with pytest.raises(InterruptedError):
        cache.prepared_turbo_voice(model, reference, data, cancel_path=cancelled)
    assert model.calls == 0


def test_worker_custom_turbo_uses_selected_voice_arrays(prepared, monkeypatch):
    model, reference, data = prepared
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(data))
    worker = importlib.import_module('worker')
    monkeypatch.setattr(worker, 'DATA', data)
    observed = []
    def infer(text, **options):
        observed.append((text, options))
        return np.zeros(480, dtype=np.float32)
    model.infer = infer
    model.save = lambda *args: None
    monkeypatch.setitem(sys.modules, 'local_vieneu', SimpleNamespace(LocalVieneu=lambda **kwargs: model))
    import voice_library
    monkeypatch.setattr(voice_library, 'resolve_reference', lambda voice, root: (reference, {'id': voice}))
    synthesize = worker.load_synthesizer({'engine': 'vieneu', 'quality': 'standard', 'voice_id': 'my-sample'})
    synthesize('First sentence.', data / 'first.wav')
    synthesize('Second sentence.', data / 'second.wav')
    assert model.calls == 1
    assert [text for text, _ in observed] == ['First sentence.', 'Second sentence.']
    assert all(set(options) == {'voice'} for _, options in observed)
    assert np.array_equal(observed[0][1]['voice']['speaker_emb'], model.embedding)
    assert np.array_equal(observed[0][1]['voice']['codes'], model.codes)
