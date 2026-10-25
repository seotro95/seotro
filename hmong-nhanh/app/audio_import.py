"""Bounded local decoding for phone recordings using a packaged FFmpeg binary."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


class AudioImportError(ValueError):
    """An input file could not be decoded safely and completely."""


class DecoderUnavailable(AudioImportError):
    """The optional media decoder needs installation."""


def ffmpeg_executable():
    # imageio-ffmpeg's wheel carries its own executable on supported platforms;
    # get_ffmpeg_exe() does not download anything at runtime.
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError, OSError):
        executable = shutil.which('ffmpeg')
        if executable:
            return executable
    raise DecoderUnavailable(
        'Chưa có bộ đọc M4A/AAC/MP4/WEBM. Mở lại MO_HMONG_NHANH.bat để cài '
        'imageio-ffmpeg, hoặc tải mẫu WAV/MP3.')


def decode_to_wav(source, destination, max_seconds=600):
    """Decode at most one second beyond the allowed duration, then validate it.

    The extra second detects overlong inputs instead of silently accepting a
    truncated recording. The caller inspects the resulting WAV and rejects it
    when it exceeds max_seconds. The output is bounded to about29MB at600s.
    """
    source, destination = Path(source), Path(destination)
    executable = ffmpeg_executable()
    command = [
        executable, '-nostdin', '-y', '-hide_banner', '-loglevel', 'error', '-xerror',
        '-protocol_whitelist', 'file,pipe',
        '-format_whitelist', 'mov,aac,matroska,webm,mp3,wav,flac,ogg',
        '-i', str(source.resolve()), '-map', '0:a:0', '-vn', '-sn', '-dn',
        '-threads', '1', '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le',
        '-t', str(max_seconds + 1), '-f', 'wav', str(destination.resolve()),
    ]
    try:
        subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.PIPE, check=True, timeout=120)
        if not destination.is_file() or destination.stat().st_size <= 44:
            raise AudioImportError('Tệp không có luồng âm thanh đọc được.')
        # Includes generous space for a WAV header; never trust the container's
        # reported duration as the only bound on disk output.
        if destination.stat().st_size > (max_seconds + 1) * 24000 * 2 + 65536:
            raise AudioImportError('Tệp âm thanh sau giải mã vượt giới hạn 10 phút.')
    except subprocess.TimeoutExpired:
        destination.unlink(missing_ok=True)
        raise AudioImportError('Giải mã mẫu quá lâu. Thử xuất đoạn rõ lời thành WAV hoặc MP3 rồi tải lại.') from None
    except (OSError, subprocess.CalledProcessError):
        destination.unlink(missing_ok=True)
        raise AudioImportError(
            'Không đọc được âm thanh trong tệp. Chọn WAV, MP3, FLAC, OGG, '
            'M4A, AAC, MP4 hoặc WEBM có tiếng, dài 3 giây đến 10 phút.') from None
    except AudioImportError:
        destination.unlink(missing_ok=True)
        raise
    return destination
