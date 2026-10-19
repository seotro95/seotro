"""Conservative, local audio cleanup without changing speech timing.

References are prepared once for the voice cache. Final audio is filtered once
after subtitle assembly, so silence and cue positions remain in the same place.
FFmpeg does the signal processing and the long-file work; Python only reads
bounded chunks to validate the result before publishing it atomically.
"""
from __future__ import annotations

import array
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import wave


SAMPLE_RATE = 24_000
MAX_REFERENCE_BYTES = 200 * 1024 * 1024
MAX_AUDIO_SECONDS = 24 * 60 * 60
LEVELS = frozenset({"off", "light", "strong"})
# afftdn uses a 25 ms lookahead. Supplying exactly that much tail and removing
# exactly its artificial leading delay preserves every original speech frame.
DENOISE_DELAY = SAMPLE_RATE // 40


def _level(value: str) -> str:
    if not isinstance(value, str) or value not in LEVELS:
        raise ValueError("Mức lọc âm cần là off, light hoặc strong.")
    return value


def _source(value: str | Path) -> Path:
    # No shell and no URLs: even playlists can only open local file/pipe input.
    try:
        path = Path(value).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("Không tìm thấy tệp âm thanh trên máy.") from exc
    if not path.is_file():
        raise ValueError("Cần chọn một tệp âm thanh trên máy.")
    return path


def _destination(value: str | Path) -> Path:
    path = Path(value).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _filters(level: str, *, reference: bool) -> str:
    if level == "off":
        return "anull"
    # No gate, compressor, speech trimming or silence removal: these can
    # discard breaths, consonants and pauses used by tonal Hmong speech.
    reduction = 6 if level == "light" else 12
    filters = [f"apad=pad_len={DENOISE_DELAY}", "highpass=f=55",
               f"afftdn=nr={reduction}:nf=-60:tn=1:gs=5",
               f"atrim=start_sample={DENOISE_DELAY}", "asetpts=PTS-STARTPTS"]
    if reference:
        filters.extend(["loudnorm=I=-20:TP=-2:LRA=11", f"aresample={SAMPLE_RATE}"])
    filters.append("alimiter=limit=0.96:level=false:latency=true")
    return ",".join(filters)


def _run_ffmpeg(command: list[str], folder: Path, timeout: float) -> None:
    # stderr stays on disk rather than accumulating with a multi-hour file.
    with tempfile.TemporaryFile(dir=folder) as errors:
        try:
            subprocess.run(command, stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=errors,
                           timeout=timeout, check=True)
        except (subprocess.SubprocessError, OSError) as exc:
            errors.seek(0, 2)
            length = errors.tell()
            errors.seek(max(0, length - 4096))
            detail = errors.read(4096).decode("utf-8", errors="replace").strip()
            raise RuntimeError("Không lọc được âm thanh bằng FFmpeg. " + detail) from exc
        # subprocess.run kills and waits for its own child on cancellation;
        # TemporaryDirectory in the caller removes the unpublished result.


def _pcm_info(path: Path, *, scan: bool = True, minimum: int = 1,
              maximum: int = MAX_AUDIO_SECONDS * SAMPLE_RATE,
              unclipped: bool = False) -> tuple[int, int]:
    """Validate mono PCM16 24 kHz with bounded memory; return frames and peak."""
    try:
        with wave.open(str(path), "rb") as audio:
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(),
                    audio.getcomptype()) != (1, 2, SAMPLE_RATE, "NONE"):
                raise ValueError("Âm thanh cần là WAV PCM16 mono 24 kHz.")
            frames = audio.getnframes()
            if not minimum <= frames <= maximum:
                raise ValueError("Thời lượng âm thanh không hợp lệ.")
            if not scan:
                return frames, 0
            # The clone runtime already requires NumPy. Keep imports lazy so
            # merely showing the app does not load its native libraries, and
            # retain a small stdlib fallback for the base/diagnostic runtime.
            try:
                import numpy as np
            except ImportError:
                np = None
            count, peak = 0, 0
            while raw := audio.readframes(65_536):
                count += len(raw)
                if np is not None:
                    # Widen before abs: abs(PCM16 -32768) overflows int16.
                    samples = np.frombuffer(raw, dtype="<i2").astype(np.int32)
                    peak = max(peak, int(np.max(np.abs(samples))))
                else:
                    samples = array.array("h")
                    samples.frombytes(raw)
                    if sys.byteorder != "little":
                        samples.byteswap()
                    peak = max(peak, abs(min(samples)), abs(max(samples)))
            if count != frames * 2:
                raise ValueError("Tệp WAV bị thiếu dữ liệu.")
            if peak == 0:
                raise ValueError("Tệp âm thanh chỉ có im lặng.")
            if unclipped and peak >= 32768:
                raise ValueError("Âm thanh vượt quá biên độ an toàn.")
            return frames, peak
    except (wave.Error, EOFError, OSError) as exc:
        raise ValueError("Không đọc được tệp WAV hợp lệ.") from exc


def clean_reference(source: str | Path, destination: str | Path,
                    level: str = "light", max_seconds: float = 10) -> Path:
    """Prepare <=10 seconds of a reference while preserving the original.

    ``off`` only decodes, downmixes and resamples. ``light`` removes low rumble
    and gently reduces steady noise, then normalizes reference loudness.
    ``strong`` can change vocal timbre and should be chosen explicitly.
    """
    level = _level(level)
    if (isinstance(max_seconds, bool) or not isinstance(max_seconds, (float, int))
            or not math.isfinite(max_seconds) or not 1 <= max_seconds <= 10):
        raise ValueError("Mẫu xử lý cần dài từ 1 đến 10 giây.")
    original = _source(source)
    target = _destination(destination)
    if original == target or (target.exists() and original.samefile(target)):
        raise ValueError("Tệp đã lọc cần khác tệp mẫu gốc.")
    if original.stat().st_size > MAX_REFERENCE_BYTES:
        raise ValueError("Mẫu giọng không được vượt quá 200 MB.")
    with tempfile.TemporaryDirectory(prefix=".audio-clean-", dir=target.parent) as temporary:
        folder = Path(temporary)
        decoded = folder / "decoded.wav"
        command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-xerror",
                   "-protocol_whitelist", "file,pipe", "-i", str(original),
                   "-t", str(max_seconds), "-map", "0:a:0", "-vn", "-sn", "-dn",
                   "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le",
                   "-f", "wav", str(decoded)]
        _run_ffmpeg(command, folder, timeout=120)
        # Check the actual decoded reference before normalization can amplify
        # codec noise/dither from an otherwise completely silent recording.
        frames, _ = _pcm_info(decoded, minimum=SAMPLE_RATE,
                              maximum=math.ceil(max_seconds * SAMPLE_RATE))
        result = decoded
        if level != "off":
            result = folder / "reference.wav"
            command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-xerror",
                       "-protocol_whitelist", "file,pipe", "-i", str(decoded),
                       "-af", _filters(level, reference=True), "-ac", "1",
                       "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", "-f", "wav", str(result)]
            _run_ffmpeg(command, folder, timeout=120)
        actual, _ = _pcm_info(result, minimum=SAMPLE_RATE,
                             maximum=math.ceil(max_seconds * SAMPLE_RATE), unclipped=True)
        if actual != frames:
            raise RuntimeError("Bộ lọc làm đổi thời lượng mẫu; giữ nguyên tệp trước đó.")
        result.replace(target)
    return target


def polish_audio(source: str | Path, destination: str | Path,
                 level: str = "light") -> Path:
    """Stream a generated WAV through cleanup and keep exactly every frame.

    The source must be the engine's mono PCM16 24 kHz WAV, at most 24 hours.
    No global gain is added to finished audio. ``off`` copies bytes unchanged.
    An in-place call is safe: a failed/cancelled filter never replaces source.
    """
    level = _level(level)
    original = _source(source)
    target = _destination(destination)
    frames, _ = _pcm_info(original, scan=False)
    if level == "off" and original == target:
        _pcm_info(original)
        return target
    with tempfile.TemporaryDirectory(prefix=".audio-clean-", dir=target.parent) as temporary:
        folder = Path(temporary)
        result = folder / "finished.wav"
        if level == "off":
            with original.open("rb") as reader, result.open("wb") as writer:
                shutil.copyfileobj(reader, writer, length=1024 * 1024)
        else:
            command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-xerror",
                       "-protocol_whitelist", "file,pipe", "-i", str(original),
                       "-map", "0:a:0", "-vn", "-sn", "-dn",
                       "-af", _filters(level, reference=False), "-ac", "1",
                       "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", "-f", "wav", str(result)]
            _run_ffmpeg(command, folder, timeout=max(120, frames / SAMPLE_RATE * 0.5))
        actual, _ = _pcm_info(result, unclipped=level != "off")
        if actual != frames:
            raise RuntimeError("Bộ lọc làm đổi thời lượng; giữ nguyên tệp âm thanh trước đó.")
        result.replace(target)
    return target
