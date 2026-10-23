"""Pinned, offline model integrity checks for the experimental fast backend.

Importing this module does not import PyTorch or download model files. The
manifest records installation provenance; the constants below remain the
authority for file sizes and hashes even if a local manifest is modified.
"""
from __future__ import annotations

import json
from pathlib import Path
import threading

from hmong_engine import EngineError, _file_fingerprint, _sha256, model_directory


MANIFEST_NAME = "verified-native-models.json"


def _record(repository, revision, remote, size, sha256, *, space=False):
    prefix = "https://huggingface.co/" + ("spaces/" if space else "")
    return {
        "repository": repository,
        "revision": revision,
        "remote": remote,
        "url": prefix + repository + "/resolve/" + revision + "/" + remote,
        "size": size,
        "sha256": sha256,
    }


MODEL_RECORDS = {
    "native-vits/G_60000.pth": _record(
        "leejnus/HmongTTS", "2e1a9f025e9df08990cb87e2851aeee5bc9f7268", "G_60000.pth",
        436823999, "91fc48eb69e5a2eb574e867ba82fda7c2df08a3d3b521457549a706b83b8449c", space=True),
    "native-vits/config.json": _record(
        "leejnus/HmongTTS", "2e1a9f025e9df08990cb87e2851aeee5bc9f7268", "hmong.json",
        1503, "7866b4a6039fc51c237795822a489f2e20608ed6cf732c558d3a24715f7bec06", space=True),
    "openvoice-v2/converter.pth": _record(
        "myshell-ai/OpenVoiceV2", "f36e7edfe1684461a8343844af60babc2efbb727", "converter/checkpoint.pth",
        131320490, "9652c27e92b6b2a91632590ac9962ef7ae2b712e5c5b7f4c34ec55ee2b37ab9e"),
    "openvoice-v2/config.json": _record(
        "myshell-ai/OpenVoiceV2", "f36e7edfe1684461a8343844af60babc2efbb727", "converter/config.json",
        838, "9dfff60350b8c63f2c664efd92a61b2516efb22671466960f0e5dfebd881fa47"),
    "wavmark/model.pth": _record(
        "M4869/WavMark", "0ad3c7b74f641bddb61f6b85cdf2de0d93a5bfef",
        "step59000_snr39.99_pesq4.35_BERP_none0.30_mean1.81_std1.81.model.pkl",
        10019039, "7a3d873d115c2c644685fb4cf109bdb299718296b88c871d3cf1c8e4cbc13144"),
}
MODEL_FILES = tuple(MODEL_RECORDS)
_integrity_cache = {}
_integrity_lock = threading.Lock()


def verify_models(root=None):
    """Check pinned bytes locally, returning a fingerprint suitable for reuse.

The cache is invalidated by filesystem identity, size, write time and change
time. On Windows, a missing native ChangeTime disables caching rather than
trusting the creation time returned by Python's stat().
    """
    root = Path(root).expanduser().resolve() if root is not None else model_directory()
    try:
        manifest_path = root / MANIFEST_NAME
        manifest_stat = manifest_path.stat()
        if not manifest_path.is_file() or not 0 < manifest_stat.st_size <= 100_000:
            raise ValueError("manifest size")
        with manifest_path.open("rb") as handle:
            raw = handle.read(100_001)
        if len(raw) > 100_000:
            raise ValueError("manifest too large")
        manifest = json.loads(raw)
        if (not isinstance(manifest, dict) or manifest.get("version") != 1
                or manifest.get("backend") != "hmong_native"):
            raise ValueError("manifest schema")
        records = manifest["files"]
        if not isinstance(records, dict):
            raise ValueError("manifest records")
        manifest_identity = _file_fingerprint(manifest_path, manifest_stat)
        fingerprint = [(str(root), *manifest_identity)]
        cacheable = manifest_identity[-1] is not None
        identities = {}
        for relative, expected in MODEL_RECORDS.items():
            record = records[relative]
            if not isinstance(record, dict) or any(record.get(key) != value for key, value in expected.items()):
                raise ValueError("manifest differs from pinned model")
            path = root / relative
            stat = path.stat()
            if not path.is_file() or stat.st_size != expected["size"]:
                raise ValueError("file size")
            identity = _file_fingerprint(path, stat)
            identities[relative] = identity
            cacheable = cacheable and identity[-1] is not None
            fingerprint.append((relative, *identity, expected["sha256"]))
        key = tuple(fingerprint)
        with _integrity_lock:
            if cacheable and key in _integrity_cache:
                return key
            for relative, expected in MODEL_RECORDS.items():
                path = root / relative
                if _sha256(path) != expected["sha256"]:
                    raise ValueError("checksum mismatch")
                if _file_fingerprint(path, path.stat()) != identities[relative]:
                    raise ValueError("file changed during verification")
            if _file_fingerprint(manifest_path, manifest_path.stat()) != manifest_identity:
                raise ValueError("manifest changed during verification")
            _integrity_cache.clear()
            if cacheable:
                _integrity_cache[key] = True
        return key
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        raise EngineError(
            "Thiếu mô hình Hmong nhanh hoặc SHA-256 không đạt. Chạy MO_HMONG_NHANH.bat "
            "hoặc python prepare_hmong_native.py bằng mạng được phép; không dùng tệp chưa xác minh."
        ) from None
