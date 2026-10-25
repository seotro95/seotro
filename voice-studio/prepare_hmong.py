"""Download the explicitly selected community model with verified integrity.

Metadata comes from the model host's HTTPS API. LFS SHA-256 or the Git blob
identity is checked before a download is installed; every installed file also
gets a local SHA-256 manifest checked by the offline inference engine.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
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


class _InterruptedDownload(SetupError):
    pass


DOWNLOAD_ATTEMPTS = 3
DOWNLOAD_TIMEOUT = 60


@contextmanager
def _download_lock(destination):
    """Two first-launch windows must not write the same resumable file."""
    with destination.with_name(destination.name + ".download.lock").open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        try:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise SetupError("Một cửa sổ khác đang chuẩn bị " + destination.name
                             + ". Giữ cửa sổ đó mở và chờ hoàn tất trước khi thử lại.") from None
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _retry_url(url, attempt):
    # Re-resolve the SAME pinned upstream path instead of replaying an expired
    # cached CDN redirect. TLS verification and final integrity checks stay on.
    if not attempt:
        return url
    parts = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    query.append(("voice_studio_retry", str(time.time_ns())))
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def _receive_model(response, temporary, size, offset):
    status = getattr(response, "status", 200)
    headers = getattr(response, "headers", {})
    if status == 206:
        match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", headers.get("Content-Range", ""))
        if (match is None or int(match[1]) != offset or int(match[3]) != size
                or not offset <= int(match[2]) < size):
            raise SetupError("Máy chủ trả Content-Range không khớp; không nối tệp mô hình.")
        response_size = int(match[2]) - offset + 1
    elif status == 200:
        # A server may ignore Range. Replace the partial rather than appending
        # a complete response to its existing prefix.
        offset, response_size = 0, size
    else:
        raise SetupError("Máy chủ trả HTTP không hợp lệ: " + str(status))
    length = headers.get("Content-Length")
    if length is not None and (not length.isdigit() or int(length) != response_size):
        raise SetupError("Kích thước HTTP không khớp mô hình; chưa cài tệp này.")
    with temporary.open("ab" if offset else "wb") as output:
        total, last_report = offset, offset
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            total += len(block)
            if total > offset + response_size or total > size:
                raise SetupError("Tệp tải về lớn hơn metadata. Dừng để bảo vệ tính toàn vẹn.")
            output.write(block)
            if total - last_report >= 64 * 1024 * 1024:
                print(f"  {temporary.name}: {total // (1024 ** 2)}/{size // (1024 ** 2)} MiB", flush=True)
                last_report = total
    if total != size:
        raise _InterruptedDownload("Kết nối kết thúc khi mới tải " + str(total) + "/" + str(size) + " byte.")


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
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with _download_lock(destination):
        existing = _verified(destination, size, sha256, blob)
        if existing:
            print("Đã xác minh, dùng lại:", destination.name, flush=True)
            return existing
        temporary = destination.with_name(destination.name + ".part")
        for attempt in range(DOWNLOAD_ATTEMPTS):
            offset = temporary.stat().st_size if temporary.is_file() else 0
            if offset >= size:
                complete = _verified(temporary, size, sha256, blob)
                if complete:
                    temporary.replace(destination)
                    return complete
                temporary.unlink()
                offset = 0
            headers = {"User-Agent": "Hmoob-VoiceLab/1.0", "Accept-Encoding": "identity"}
            if offset:
                headers["Range"] = "bytes=" + str(offset) + "-"
                print(f"Tiếp tục tải {destination.name} từ {offset // (1024 ** 2)} MiB; kiểm tra SHA-256 khi đủ tệp.", flush=True)
            if attempt:
                headers["Cache-Control"] = "no-cache"
            request = urllib.request.Request(_retry_url(url, attempt), headers=headers)
            delay = attempt + 1
            try:
                with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:
                    _receive_model(response, temporary, size, offset)
                actual_sha = _verified(temporary, size, sha256, blob)
                if actual_sha is None:
                    temporary.unlink(missing_ok=True)
                    raise SetupError("Checksum/kích thước không khớp cho " + destination.name + "; không cài tệp này.")
                temporary.replace(destination)
                return actual_sha
            except urllib.error.HTTPError as exc:
                if exc.code not in {403, 408, 416, 429, 500, 502, 503, 504}:
                    raise
                if exc.code == 416:
                    temporary.unlink(missing_ok=True)
                retry_after = exc.headers.get("Retry-After", "") if exc.headers else ""
                if retry_after.isdigit():
                    delay = min(3, max(1, int(retry_after)))
                detail = "HTTP " + str(exc.code)
                exc.close()
            except (urllib.error.URLError, ConnectionError, TimeoutError,
                    http.client.IncompleteRead, _InterruptedDownload) as exc:
                detail = str(exc)
            if attempt + 1 == DOWNLOAD_ATTEMPTS:
                saved = temporary.stat().st_size if temporary.is_file() else 0
                raise SetupError(f"Chưa tải được {destination.name} sau {DOWNLOAD_ATTEMPTS} lần: {detail}. "
                                 f"Đã giữ {saved} byte tải dở; mở lại tool để tiếp tục. "
                                 "Nếu vẫn gặp 403, dùng mạng có quyền truy cập Hugging Face/CDN.") from None
            print(f"Tải gián đoạn ({detail}). Giữ phần đã tải; tự thử lại {attempt + 2}/{DOWNLOAD_ATTEMPTS}...", flush=True)
            time.sleep(delay)


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
