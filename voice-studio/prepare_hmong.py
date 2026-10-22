"""Download the explicitly selected community model with verified integrity.

Metadata comes from the model host's HTTPS API. LFS SHA-256 or the Git blob
identity is checked before a download is installed; every installed file also
gets a local SHA-256 manifest checked by the offline inference engine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

from hmong_engine import EngineError, model_directory, verify_models


SOURCES = (
    ("Pakorn2112/F5TTS-Hmong", {
        "model_159952.safetensors": "f5-hmong/model_159952.safetensors",
        "vocab.txt": "f5-hmong/vocab.txt",
    }),
    ("charactr/vocos-mel-24khz", {
        "config.yaml": "vocos/config.yaml",
        "pytorch_model.bin": "vocos/pytorch_model.bin",
    }),
)
MODEL_REVISIONS = {
    "Pakorn2112/F5TTS-Hmong": "c50fc0cc991bc0c4f22d86c7a6152730c667c0d5",
    "charactr/vocos-mel-24khz": "0feb3fdd929bcd6649e0e7c5a688cf7dd012ef21",
}


class SetupError(RuntimeError):
    pass


def _get_metadata(repository):
    expected_revision = MODEL_REVISIONS[repository]
    url = "https://huggingface.co/api/models/" + repository + "/revision/" + expected_revision + "?blobs=true"
    request = urllib.request.Request(url, headers={"User-Agent": "Voice-Studio-Hmong/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise SetupError("Phản hồi metadata quá lớn; chưa tải mô hình.")
    metadata = json.loads(raw)
    revision = metadata.get("sha", "")
    if not isinstance(revision, str) or len(revision) != 40 or any(ch not in "0123456789abcdef" for ch in revision):
        raise SetupError("Máy chủ không cung cấp commit mô hình hợp lệ; không dùng bản main chưa cố định.")
    if revision != expected_revision:
        raise SetupError("Máy chủ trả phiên bản mô hình khác bản đã kiểm thử; chưa tải hoặc thay tệp cục bộ.")
    return metadata


def _entry(metadata, filename):
    siblings = metadata.get("siblings", [])
    found = [item for item in siblings if item.get("rfilename") == filename]
    if not found:
        found = [item for item in siblings if Path(item.get("rfilename", "")).name == filename]
    if len(found) != 1:
        raise SetupError("Không xác định được duy nhất tệp " + filename + " trong metadata chính thức.")
    item = found[0]
    name = item["rfilename"]
    if not isinstance(name, str) or name.startswith("/") or ".." in Path(name).parts:
        raise SetupError("Đường dẫn tệp mô hình không hợp lệ.")
    lfs = item.get("lfs") or {}
    sha256 = lfs.get("sha256") or lfs.get("oid")
    if isinstance(sha256, str) and sha256.startswith("sha256:"):
        sha256 = sha256[7:]
    blob = item.get("blobId")
    size = item.get("size", lfs.get("size"))
    if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= 4 * 1024 ** 3:
        raise SetupError("Máy chủ không cung cấp kích thước hợp lệ cho " + filename)
    if sha256:
        if not isinstance(sha256, str) or len(sha256) != 64 or any(ch not in "0123456789abcdef" for ch in sha256):
            raise SetupError("SHA-256 không hợp lệ cho " + filename)
    elif not isinstance(blob, str) or len(blob) != 40 or any(ch not in "0123456789abcdef" for ch in blob):
        raise SetupError("Thiếu checksum từ máy chủ cho " + filename)
    return name, size, sha256, blob


def _hashes(path, size):
    sha256 = hashlib.sha256()
    git_blob = hashlib.sha1(b"blob " + str(size).encode("ascii") + b"\0")
    total = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            total += len(block)
            sha256.update(block)
            git_blob.update(block)
    return total, sha256.hexdigest(), git_blob.hexdigest()


def _verified(path, size, sha256, blob):
    if not path.is_file() or path.stat().st_size != size:
        return None
    actual_size, actual_sha, actual_blob = _hashes(path, size)
    if actual_size == size and (actual_sha == sha256 if sha256 else actual_blob == blob):
        return actual_sha
    return None


def _download(url, destination, size, sha256, blob):
    existing = _verified(destination, size, sha256, blob)
    if existing:
        print("Đã xác minh, dùng lại:", destination.name, flush=True)
        return existing
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=destination.name + ".", suffix=".part", dir=destination.parent)
    temporary = Path(temporary)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Hmoob-VoiceLab/1.0"})
        with os.fdopen(fd, "wb") as output, urllib.request.urlopen(request, timeout=120) as response:
            total = 0
            last_report = 0
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > size:
                    raise SetupError("Tệp tải về lớn hơn metadata. Dừng để bảo vệ tính toàn vẹn.")
                output.write(block)
                if total - last_report >= 64 * 1024 * 1024:
                    print(f"  {destination.name}: {total // (1024 ** 2)}/{size // (1024 ** 2)} MiB", flush=True)
                    last_report = total
        actual_sha = _verified(temporary, size, sha256, blob)
        if actual_sha is None:
            raise SetupError("Checksum/kích thước không khớp cho " + destination.name + "; không cài tệp này.")
        temporary.replace(destination)
        return actual_sha
    finally:
        temporary.unlink(missing_ok=True)


def install(root):
    root = Path(root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    manifest = {"version": 1, "sources": [], "files": {}}
    for repository, mapping in SOURCES:
        print("Đọc metadata:", repository, flush=True)
        metadata = _get_metadata(repository)
        revision = metadata["sha"]
        manifest["sources"].append({"repository": repository, "revision": revision})
        for filename, relative in mapping.items():
            remote, size, expected_sha, blob = _entry(metadata, filename)
            url = "https://huggingface.co/" + repository + "/resolve/" + revision + "/" + urllib.parse.quote(remote, safe="/")
            print("Kiểm tra/tải:", remote, flush=True)
            actual_sha = _download(url, root / relative, size, expected_sha, blob)
            manifest["files"][relative] = {"sha256": actual_sha, "size": size, "url": url}
    fd, temporary = tempfile.mkstemp(prefix="manifest-", suffix=".json", dir=root)
    temporary = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temporary.replace(root / "verified-models.json")
    finally:
        temporary.unlink(missing_ok=True)
    verify_models(root)
    print("Đã xác minh toàn bộ mô hình. Mở tool, chọn giọng và nghe thử một câu trước khi đọc dài.", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Cài F5-Hmong cục bộ với checksum từ nguồn HTTPS chính thức.")
    parser.add_argument("--model-dir", type=Path, default=model_directory())
    parser.add_argument("--verify-only", action="store_true", help="Chỉ xác minh tệp đã tải, không dùng mạng")
    args = parser.parse_args(argv)
    try:
        if args.verify_only:
            verify_models(args.model_dir)
            print("Kiểm tra SHA-256 thành công.")
        else:
            install(args.model_dir)
        return 0
    except (EngineError, SetupError, OSError, urllib.error.URLError, ValueError) as exc:
        print("Chưa cài được giọng:", str(exc), file=sys.stderr)
        print("Không tắt TLS hoặc bỏ checksum. Kiểm tra mạng tới huggingface.co và các CDN Hugging Face; "
              "mở lại tool sau khi cài xong.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
