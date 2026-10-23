"""Native model provenance and offline integrity, using small local fixtures."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

import pytest

import hmong_native_models as models
import prepare_hmong_native as setup


@pytest.fixture
def tiny_models(tmp_path, monkeypatch):
    records, contents = {}, {}
    for index, (relative, original) in enumerate(models.MODEL_RECORDS.items()):
        payload = f"pinned fixture {index}\n".encode()
        contents[relative] = payload
        records[relative] = dict(original, size=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    monkeypatch.setattr(models, "MODEL_RECORDS", records)
    monkeypatch.setattr(setup, "MODEL_RECORDS", records)
    models._integrity_cache.clear()
    return tmp_path, records, contents


def write_fixture(fixture):
    root, records, contents = fixture
    for relative, payload in contents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    (root / models.MANIFEST_NAME).write_text(json.dumps({
        "version": 1, "backend": "hmong_native", "files": records,
    }), encoding="utf-8")
    return root


def test_imports_do_not_load_inference_or_contact_network():
    source = """
import sys
import urllib.request
def blocked(*args, **kwargs):
    raise AssertionError('network on import')
urllib.request.urlopen = blocked
import hmong_native_models
import prepare_hmong_native
assert not any(name in sys.modules for name in ('torch', 'torchaudio', 'numpy', 'hmong_native'))
"""
    result = subprocess.run([sys.executable, "-c", source], cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr


def test_all_model_urls_are_pinned_and_expected_sizes_are_coded():
    assert len(models.MODEL_RECORDS) == 5
    assert sum(record["size"] for record in models.MODEL_RECORDS.values()) == 578165869
    assert models.MANIFEST_NAME != "verified-models.json"
    for relative, record in models.MODEL_RECORDS.items():
        assert record["url"].startswith("https://huggingface.co/")
        assert "/resolve/" + record["revision"] + "/" in record["url"]
        assert len(record["revision"]) == 40 and all(char in "0123456789abcdef" for char in record["revision"])
        assert record["url"].endswith("/" + record["remote"])
        assert len(record["sha256"]) == 64 and all(char in "0123456789abcdef" for char in record["sha256"])
        assert not Path(relative).is_absolute() and ".." not in Path(relative).parts
    assert models.MODEL_RECORDS["native-vits/G_60000.pth"]["sha256"] == "91fc48eb69e5a2eb574e867ba82fda7c2df08a3d3b521457549a706b83b8449c"
    assert models.MODEL_RECORDS["openvoice-v2/converter.pth"]["sha256"] == "9652c27e92b6b2a91632590ac9962ef7ae2b712e5c5b7f4c34ec55ee2b37ab9e"
    assert models.MODEL_RECORDS["wavmark/model.pth"]["sha256"] == "7a3d873d115c2c644685fb4cf109bdb299718296b88c871d3cf1c8e4cbc13144"


def test_model_directory_uses_the_shared_override(tmp_path, monkeypatch):
    monkeypatch.setenv("HMOOB_MODEL_DIR", str(tmp_path / "chosen models"))
    assert models.model_directory() == (tmp_path / "chosen models").resolve()


@pytest.mark.parametrize("installed", [False, True])
def test_verify_only_never_downloads(tiny_models, monkeypatch, installed):
    root = write_fixture(tiny_models) if installed else tiny_models[0]
    def blocked(*args, **kwargs):
        pytest.fail("--verify-only must not download or contact a server")
    monkeypatch.setattr(setup, "_download", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)
    assert setup.main(["--model-dir", str(root), "--verify-only"]) == (0 if installed else 1)
    assert (root / models.MANIFEST_NAME).exists() is installed


def test_manifest_cannot_redefine_a_pinned_checksum(tiny_models):
    root = write_fixture(tiny_models)
    relative = next(iter(tiny_models[1]))
    path = root / relative
    malicious = b"x" * path.stat().st_size
    path.write_bytes(malicious)
    manifest_path = root / models.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][relative]["sha256"] = hashlib.sha256(malicious).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(models.EngineError, match="SHA-256"):
        models.verify_models(root)


def test_manifest_marker_without_bytes_is_never_ready(tiny_models):
    root, records, _ = tiny_models
    (root / models.MANIFEST_NAME).write_text(json.dumps({
        "version": 1, "backend": "hmong_native", "files": records,
    }), encoding="utf-8")
    with pytest.raises(models.EngineError):
        models.verify_models(root)


def test_same_size_overwrite_with_restored_mtime_invalidates_cache(tiny_models):
    root = write_fixture(tiny_models)
    models.verify_models(root)
    path = root / next(iter(tiny_models[1]))
    original_stat = path.stat()
    path.write_bytes(b"!" * original_stat.st_size)
    os.utime(path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    with pytest.raises(models.EngineError, match="SHA-256"):
        models.verify_models(root)


def test_missing_windows_change_time_disables_cache(tiny_models, monkeypatch):
    root = write_fixture(tiny_models)
    fingerprint = models._file_fingerprint
    monkeypatch.setattr(models, "_file_fingerprint", lambda path, stat: (*fingerprint(path, stat)[:-1], None))
    models.verify_models(root)
    assert not models._integrity_cache
    path = root / next(iter(tiny_models[1]))
    stat = path.stat()
    path.write_bytes(b"!" * stat.st_size)
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    with pytest.raises(models.EngineError):
        models.verify_models(root)


def test_install_uses_fixed_urls_and_preserves_f5_and_personal_files(tiny_models, monkeypatch):
    root, records, contents = tiny_models
    preserved = {"verified-models.json": b"F5 manifest unchanged", "f5-hmong/personal.pth": b"F5 model", "voices/my-voice.json": b"personal"}
    for relative, data in preserved.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    requests = []
    def download(request, timeout):
        requests.append((request.full_url, timeout))
        relative = next(relative for relative, record in records.items() if record["url"] == request.full_url)
        return io.BytesIO(contents[relative])
    monkeypatch.setattr(urllib.request, "urlopen", download)
    setup.install(root)
    assert [url for url, _ in requests] == [record["url"] for record in records.values()]
    assert models.verify_models(root)
    for relative, data in preserved.items():
        assert (root / relative).read_bytes() == data
    assert not list(root.rglob("*.part"))
    # Running again verifies existing bytes and is safe without a network.
    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: pytest.fail("valid models should be reused"))
    setup.install(root)


def test_failed_checksum_cannot_replace_existing_file_or_mark_ready(tiny_models, monkeypatch):
    root, records, _ = tiny_models
    relative = next(iter(records))
    path = root / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(b"old installation")
    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: io.BytesIO(b"x" * records[relative]["size"]))
    assert setup.main(["--model-dir", str(root)]) == 1
    assert path.read_bytes() == b"old installation"
    assert not (root / models.MANIFEST_NAME).exists()
    assert not list(root.rglob("*.part"))
