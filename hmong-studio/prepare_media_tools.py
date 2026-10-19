"""Install verified Windows FFmpeg locally without changing the system PATH.

The rolling upstream release is authenticated through HTTPS and its accompanying
SHA256 manifest. The exact expected digest and source are retained with the tools.
Only the setup helper writes this folder; existing folders are preserved on repair.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import uuid
import zipfile


BASE = Path(__file__).resolve().parent
FFMPEG_BASE = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
FFMPEG_ASSET = "ffmpeg-n8.1-latest-win64-gpl-8.1.zip"
MAX_DOWNLOAD = 512 * 1024 * 1024
MAX_UNPACKED = 2 * 1024 * 1024 * 1024


class _HTTPSRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme != "https":
            raise RuntimeError("Tu choi chuyen huong tai FFmpeg khong dung HTTPS.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open(url):
    if urllib.parse.urlsplit(url).scheme != "https":
        raise ValueError("FFmpeg downloads require HTTPS.")
    request = urllib.request.Request(url, headers={"User-Agent": "Hmong-Studio-setup/0.4"})
    return urllib.request.build_opener(_HTTPSRedirect()).open(request, timeout=60)


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_checksum(manifest, asset=FFMPEG_ASSET):
    matches = []
    for line in manifest.splitlines():
        parts = line.strip().split()
        if len(parts) == 2 and parts[1].lstrip("*") == asset:
            if not re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
                raise ValueError("Checksum FFmpeg khong hop le.")
            matches.append(parts[0].lower())
    if len(matches) != 1:
        raise ValueError("Khong tim thay duy nhat checksum cho ban FFmpeg 8.1 Windows x64.")
    return matches[0]


def _local_directory(path, base):
    base = Path(base).resolve()
    path = Path(path)
    if not path.resolve().is_relative_to(base):
        raise ValueError("Thu muc FFmpeg nam ngoai thu muc ung dung.")
    path.mkdir(parents=True, exist_ok=True)
    return path


def download_archive(downloads):
    with _open(FFMPEG_BASE + "checksums.sha256") as response:
        manifest = response.read(2 * 1024 * 1024 + 1)
    if len(manifest) > 2 * 1024 * 1024:
        raise ValueError("Manifest FFmpeg lon bat thuong.")
    expected = parse_checksum(manifest.decode("utf-8"))
    archive = Path(downloads) / FFMPEG_ASSET
    if archive.is_symlink():
        raise ValueError("Tu choi ghi de lien ket tai archive FFmpeg.")
    if not archive.is_file() or _sha256(archive) != expected:
        print("Dang tai FFmpeg 8.1 Windows x64 tu BtbN...", flush=True)
        descriptor, temporary = tempfile.mkstemp(prefix="ffmpeg-", suffix=".part", dir=downloads)
        temporary = Path(temporary)
        try:
            with os.fdopen(descriptor, "wb") as output, _open(FFMPEG_BASE + FFMPEG_ASSET) as response:
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_DOWNLOAD:
                        raise ValueError("Archive FFmpeg lon bat thuong.")
                    output.write(chunk)
            if _sha256(temporary) != expected:
                raise RuntimeError("FFmpeg SHA256 khong khop. Dung cai dat; khong dung archive nay.")
            temporary.replace(archive)
        finally:
            temporary.unlink(missing_ok=True)
    provenance = expected + "  " + FFMPEG_ASSET + "\n" + FFMPEG_BASE + "checksums.sha256\n"
    checksum_file = archive.with_suffix(".zip.sha256")
    if checksum_file.is_symlink():
        raise ValueError("Tu choi ghi de lien ket tai checksum FFmpeg.")
    checksum_file.write_text(provenance, encoding="utf-8")
    return archive, expected


def extract_verified_archive(archive, expected, target):
    """Validate the whole ZIP before writing; retain all licenses and docs."""
    if not re.fullmatch(r"[0-9a-f]{64}", expected) or _sha256(archive) != expected:
        raise RuntimeError("FFmpeg SHA256 khong khop. Khong giai nen.")
    target = Path(target)
    if target.exists() and any(target.iterdir()):
        raise ValueError("Chi giai nen vao thu muc tam trong.")
    target.mkdir(parents=True, exist_ok=True)
    root = FFMPEG_ASSET[:-4]
    with zipfile.ZipFile(archive) as bundle:
        entries = []
        names = set()
        size = 0
        for entry in bundle.infolist():
            name = entry.filename
            path = PurePosixPath(name)
            if ("\\" in name or path.is_absolute() or not path.parts or
                    any(part in (".", "..") or ":" in part for part in path.parts) or
                    path.parts[0] != root):
                raise ValueError("Duong dan khong an toan trong archive FFmpeg.")
            mode = entry.external_attr >> 16
            kind = stat.S_IFMT(mode)
            if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError("Lien ket hoac file dac biet trong archive FFmpeg.")
            parts = path.parts[1:]
            if not parts:
                continue
            relative = PurePosixPath(*parts)
            key = str(relative).casefold()
            if key in names:
                raise ValueError("Ten file trung trong archive FFmpeg.")
            names.add(key)
            size += entry.file_size
            if size > MAX_UNPACKED:
                raise ValueError("Archive FFmpeg giai nen lon bat thuong.")
            entries.append((entry, relative))
        if not {"bin/ffmpeg.exe", "bin/ffprobe.exe"}.issubset(names):
            raise ValueError("Archive thieu ffmpeg.exe hoac ffprobe.exe.")
        if not any(name.startswith("license") for name in names):
            raise ValueError("Archive thieu giay phep FFmpeg.")
        for entry, relative in entries:
            if relative.name.casefold() == "ffplay.exe":
                continue
            destination = target.joinpath(*relative.parts)
            if entry.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(entry) as source, destination.open("xb") as output:
                shutil.copyfileobj(source, output)
    (target / "UPSTREAM-SHA256.txt").write_text(
        expected + "  " + FFMPEG_ASSET + "\n" + FFMPEG_BASE + "checksums.sha256\n",
        encoding="utf-8",
    )


def tools_available(bin_directory=None):
    for name in ("ffmpeg", "ffprobe"):
        executable = (str(Path(bin_directory) / (name + ".exe")) if bin_directory
                      else shutil.which(name))
        if not executable or not Path(executable).is_file():
            return False
        try:
            result = subprocess.run([executable, "-version"], stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    timeout=20, check=False)
        except (OSError, subprocess.SubprocessError):
            return False
        if result.returncode:
            return False
    return True


def prepare(base=BASE):
    target = Path(base) / ".data" / "tools" / "ffmpeg"
    if tools_available(target / "bin") or tools_available():
        print("FFmpeg va FFprobe da san sang.", flush=True)
        return
    if os.name != "nt":
        raise RuntimeError("Can cai FFmpeg va FFprobe bang trinh quan ly goi cua he dieu hanh.")
    if sys.maxsize <= 2**32:
        raise RuntimeError("Can Python Windows 64-bit de cai FFmpeg Windows x64.")
    tools = _local_directory(Path(base) / ".data" / "tools", base)
    downloads = _local_directory(tools / "downloads", base)
    if target.is_symlink() or not target.resolve().is_relative_to(Path(base).resolve()):
        raise ValueError("Thu muc FFmpeg khong an toan.")
    archive, expected = download_archive(downloads)
    with tempfile.TemporaryDirectory(prefix=".ffmpeg-", dir=tools) as temporary:
        stage = Path(temporary) / "ffmpeg"
        extract_verified_archive(archive, expected, stage)
        if not tools_available(stage / "bin"):
            raise RuntimeError("FFmpeg Windows vua tai khong khoi dong duoc. Chua thay bo cu.")
        backup = None
        if target.exists():
            backup = tools / ("ffmpeg-backup-" + uuid.uuid4().hex[:12])
            target.rename(backup)
        try:
            stage.rename(target)
        except Exception:
            if backup is not None:
                backup.rename(target)
            raise
    print("Da cai FFmpeg co xac minh SHA256 tai .data/tools/ffmpeg.", flush=True)


if __name__ == "__main__":
    try:
        prepare()
    except Exception as exc:
        print("Chua cai duoc FFmpeg: " + str(exc), file=sys.stderr)
        sys.exit(1)
