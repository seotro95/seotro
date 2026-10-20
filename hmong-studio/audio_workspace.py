"""Local reference library and audio export; storing a sample does not clone it."""
from __future__ import annotations

import array
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid
import wave

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from starlette.concurrency import run_in_threadpool

router = APIRouter()
_ID = re.compile(r"[0-9a-f]{32}\Z")
_INPUT_FORMATS = 'wav,mp3,flac,ogg,matroska,webm,mov,mp4,m4a,3gp,3g2,mj2,aac,amr'


def _profiles_root() -> Path:
    root = Path(os.getenv('HMONG_STUDIO_DATA', str(Path(__file__).resolve().parent / '.data')))
    return root / 'profiles'


def _profile_dir(profile_id: str) -> Path:
    if not _ID.fullmatch(profile_id):
        raise HTTPException(404, 'Không tìm thấy giọng cá nhân.')
    return _profiles_root() / profile_id


def load_profile(profile_id: str) -> tuple[dict, Path]:
    """Return validated public metadata and its normalized local WAV path."""
    folder = _profile_dir(profile_id)
    try:
        # Do not follow externally substituted profile directories or audio files.
        if folder.is_symlink() or (folder / 'audio.wav').is_symlink() or (folder / 'profile.json').is_symlink():
            raise ValueError('Invalid profile path')
        metadata = json.loads((folder / 'profile.json').read_text(encoding='utf-8'))
        if metadata['id'] != profile_id or not (folder / 'audio.wav').is_file():
            raise ValueError('Invalid profile metadata')
        return {key: metadata[key] for key in ('id', 'name', 'filename', 'duration', 'language', 'url', 'transcript')}, folder / 'audio.wav'
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(404, 'Không tìm thấy giọng cá nhân.') from None


async def _upload(upload: UploadFile, destination: Path, limit: int) -> None:
    size = 0
    with destination.open('wb') as output:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                raise HTTPException(413, f'Tệp âm thanh tối đa {limit // (1024 * 1024)} MB.')
            output.write(chunk)
    if not size:
        raise HTTPException(422, 'Tệp âm thanh rỗng.')


def _ffmpeg(arguments: list[str]) -> None:
    if not shutil.which('ffmpeg'):
        raise HTTPException(503, 'Cần cài FFmpeg vào PATH rồi khởi động lại studio.')
    try:
        subprocess.run(['ffmpeg', '-nostdin', '-y', '-v', 'error', *arguments], capture_output=True, check=True, timeout=90)
    except (OSError, subprocess.SubprocessError):
        raise HTTPException(422, 'Không giải mã/xuất được âm thanh. Dùng tệp WAV, MP3, FLAC, OGG hoặc M4A hợp lệ.') from None


def _normalize(source: Path, target: Path, maximum: int) -> float:
    _ffmpeg(['-protocol_whitelist', 'file,pipe', '-format_whitelist', _INPUT_FORMATS,
             '-i', str(source), '-map', '0:a:0', '-vn', '-t', str(maximum + 1),
             '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le', '-f', 'wav', str(target)])
    try:
        with wave.open(str(target), 'rb') as wav:
            count, rate = wav.getnframes(), wav.getframerate()
            duration = count / rate
        if not math.isfinite(duration) or duration <= 0 or duration > maximum:
            raise ValueError('duration')
        return duration
    except (OSError, wave.Error, ValueError, ZeroDivisionError):
        raise HTTPException(422, f'Âm thanh phải có nội dung và dài tối đa {maximum} giây.') from None


def _validate_reference(path: Path, duration: float) -> None:
    if duration < 3:
        raise HTTPException(422, 'Mẫu giọng cần dài từ 3 đến 30 giây, một người nói và ít tạp âm.')
    with wave.open(str(path), 'rb') as wav:
        samples = array.array('h', wav.readframes(wav.getnframes()))
    if os.sys.byteorder != 'little':
        samples.byteswap()
    # Detect silence and a constant DC signal; this is not a speech-quality score.
    mean = sum(samples) / len(samples)
    variance = sum((value - mean) ** 2 for value in samples) / len(samples)
    if variance < 100:
        raise HTTPException(422, 'Mẫu giọng im lặng hoặc tín hiệu quá nhỏ. Hãy thu lại rõ tiếng.')


def _store_reference(source: Path, name: str, transcript: str, filename: str) -> dict:
    root = _profiles_root()
    root.mkdir(parents=True, exist_ok=True)
    profile_id = uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix='.upload-', dir=root) as temporary:
        staging = Path(temporary)
        duration = _normalize(source, staging / 'audio.wav', 30)
        _validate_reference(staging / 'audio.wav', duration)
        metadata = {'id': profile_id, 'name': name, 'transcript': transcript,
                    'filename': filename, 'duration': round(duration, 3), 'language': 'mww',
                    'url': f'/api/profiles/{profile_id}/audio'}
        (staging / 'profile.json').write_text(json.dumps(metadata, ensure_ascii=False), encoding='utf-8')
        # Publish both metadata and normalized audio together after validation.
        staging.rename(root / profile_id)
    return metadata


@router.get('/api/profiles')
def profiles():
    import cloning_engine
    rows = []
    root = _profiles_root()
    if root.is_dir():
        for folder in sorted(root.iterdir()):
            if _ID.fullmatch(folder.name):
                try:
                    metadata, _ = load_profile(folder.name)
                    rows.append(metadata)
                except HTTPException:
                    continue
    return {'profiles': rows, 'cloning_available': cloning_engine.availability()['ready']}


@router.post('/api/profiles', status_code=201)
async def create_profile(name: str = Form(..., min_length=1, max_length=120),
                         transcript: str = Form('', max_length=2000),
                         consent: bool = Form(False), audio: UploadFile = File(...)):
    name = name.strip()
    if not name:
        raise HTTPException(422, 'Nhập tên cho giọng cá nhân.')
    if not consent:
        raise HTTPException(422, 'Xác nhận đây là giọng của bạn hoặc bạn được chủ giọng cho phép sử dụng.')
    with tempfile.TemporaryDirectory(prefix='hmong-reference-') as temporary:
        source = Path(temporary) / 'input'
        await _upload(audio, source, 20 * 1024 * 1024)
        filename = (audio.filename or 'sample').replace('\\', '/').rsplit('/', 1)[-1][:240]
        return await run_in_threadpool(_store_reference, source, name, transcript.strip(), filename)


@router.get('/api/profiles/{profile_id}/audio')
def reference_audio(profile_id: str):
    _, path = load_profile(profile_id)
    return FileResponse(path, media_type='audio/wav', headers={'Cache-Control': 'no-store'})


@router.delete('/api/profiles/{profile_id}', status_code=204)
def delete_profile(profile_id: str):
    load_profile(profile_id)
    shutil.rmtree(_profile_dir(profile_id))
    return Response(status_code=204)


def _export(source: Path, folder: Path, output_format: str) -> bytes:
    normalized = folder / 'normalized.wav'
    _normalize(source, normalized, 600)
    if output_format == 'wav':
        return normalized.read_bytes()
    target = folder / 'output.mp3'
    _ffmpeg(['-i', str(normalized), '-vn', '-c:a', 'libmp3lame', '-b:a', '192k', str(target)])
    return target.read_bytes()


@router.post('/api/audio/export')
async def export_audio(audio: UploadFile = File(...), format: str = Form('wav')):
    if format not in ('wav', 'mp3'):
        raise HTTPException(422, 'Chọn định dạng WAV hoặc MP3.')
    with tempfile.TemporaryDirectory(prefix='hmong-export-') as temporary:
        folder = Path(temporary)
        source = folder / 'input'
        await _upload(audio, source, 50 * 1024 * 1024)
        data = await run_in_threadpool(_export, source, folder, format)
    return Response(data, media_type='audio/wav' if format == 'wav' else 'audio/mpeg',
                    headers={'Content-Disposition': f'attachment; filename="hmong-studio.{format}"', 'Cache-Control': 'no-store'})
