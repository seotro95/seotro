"""Private, offline transcription of a reference whose transcript is missing.

The small multilingual ASR model runs once in its own interpreter. Its optional
dependencies never enter the Nano/Turbo process, and cached text stays local.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import threading
import wave

from state_io import write_json_atomic

BASE = Path(__file__).resolve().parent
ASR_REPOSITORY = 'Systran/faster-whisper-base'
ASR_REVISION = 'ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66'
ASR_VERSION = '1.2.1'
ASR_FILES = frozenset({'config.json', 'model.bin', 'tokenizer.json', 'vocabulary.txt'})
_SHA256 = re.compile(r'[0-9a-f]{64}')
_lock = threading.RLock()
_MAX_TEXT = 8000


def _language(language):
    codes = {'vi', 'en', 'fr', 'ja', 'ko', 'zh', 'de', 'es', 'it', 'pt', 'ru',
             'th', 'ar', 'hi', 'id', 'tr', 'nl', 'pl', 'bn'}
    if not isinstance(language, str):
        raise ValueError('Ngôn ngữ mẫu giọng chưa được hỗ trợ để nhận dạng ngoại tuyến.')
    code = {'en-US': 'en', 'en-GB': 'en'}.get(language, language)
    if code not in codes:
        raise ValueError('Ngôn ngữ mẫu giọng chưa được hỗ trợ để nhận dạng ngoại tuyến.')
    return code


def _reference_metadata(reference):
    path = Path(reference).resolve()
    before = path.stat()
    if before.st_size > 64 * 1024**2:
        raise ValueError('Tệp WAV mẫu giọng quá lớn để nhận dạng ngoại tuyến.')
    nonzero, count = False, 0
    try:
        with wave.open(str(path), 'rb') as audio:
            channels, width, rate, frames = (audio.getnchannels(), audio.getsampwidth(),
                                             audio.getframerate(), audio.getnframes())
            if (audio.getcomptype() != 'NONE' or channels not in {1, 2} or width not in {1, 2, 3, 4}
                    or not 8000 <= rate <= 192000 or not 3 <= frames / rate <= 30):
                raise ValueError('Nhận dạng mẫu giọng cần WAV PCM dài từ 3 đến 30 giây.')
            while block := audio.readframes(65536):
                count += len(block)
                nonzero = nonzero or (any(sample != 128 for sample in block) if width == 1 else any(block))
        if count != frames * channels * width:
            raise ValueError('Dữ liệu WAV mẫu giọng bị thiếu hoặc hỏng.')
        if not nonzero:
            raise ValueError('Mẫu giọng chỉ có im lặng; không tạo lời mẫu tự động.')
    except (wave.Error, EOFError):
        raise ValueError('Không đọc được mẫu giọng dưới dạng WAV PCM.') from None
    with path.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError('Mẫu giọng đã thay đổi trong lúc nhận dạng; hãy thử lại.')
    return path, digest


def _asr_manifest(data, verify=False):
    models = Path(data).resolve()/'models'
    model = models/'native-asr'
    manifest = model/'VOICE-STUDIO-ASR.json'
    if not model.resolve().is_relative_to(models.resolve()):
        raise ValueError('Đường dẫn mô hình nhận dạng ngoại tuyến không hợp lệ.')
    try:
        if manifest.stat().st_size > 1024**2:
            raise ValueError('Bản ghi mô hình nhận dạng ngoại tuyến quá lớn.')
        record = json.loads(manifest.read_text(encoding='utf-8'))
        if (not isinstance(record, dict) or record.get('schema') != 1
                or record.get('repository') != ASR_REPOSITORY or record.get('revision') != ASR_REVISION
                or record.get('package') != 'faster-whisper' or record.get('version') != ASR_VERSION):
            raise ValueError('Mô hình nhận dạng ngoại tuyến không đúng phiên bản đã chuẩn bị.')
        entries = record.get('files')
        if not isinstance(entries, list) or len(entries) != len(ASR_FILES):
            raise ValueError('Bản ghi nhận dạng ngoại tuyến thiếu danh sách tệp.')
        seen = set()
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError('Bản ghi tệp nhận dạng ngoại tuyến không hợp lệ.')
            name, size, digest = entry.get('name'), entry.get('size'), entry.get('sha256')
            if (not isinstance(name, str) or name not in ASR_FILES or name in seen
                    or PurePosixPath(name).name != name or type(size) is not int or size <= 0
                    or not isinstance(digest, str) or not _SHA256.fullmatch(digest)):
                raise ValueError('Bản ghi tệp nhận dạng ngoại tuyến không hợp lệ.')
            seen.add(name)
            path = model/name
            if not path.resolve().is_relative_to(model.resolve()) or path.stat().st_size != size:
                raise ValueError('Tệp nhận dạng ngoại tuyến thiếu hoặc sai dung lượng.')
            if verify:
                with path.open('rb') as source:
                    actual = hashlib.file_digest(source, 'sha256').hexdigest()
                if actual != digest:
                    raise ValueError('SHA256 mô hình nhận dạng ngoại tuyến không khớp.')
        if seen != ASR_FILES:
            raise ValueError('Mô hình nhận dạng ngoại tuyến thiếu tệp bắt buộc.')
    except FileNotFoundError:
        raise ValueError('Thiếu bộ nhận dạng lời mẫu ngoại tuyến. Chạy TAI_GIONG_DA_NGON_NGU_NHANH.bat rồi thử lại.') from None
    except (json.JSONDecodeError, UnicodeError):
        raise ValueError('Bản ghi nhận dạng ngoại tuyến bị hỏng. Chạy lại TAI_GIONG_DA_NGON_NGU_NHANH.bat.') from None
    canonical = json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return model, record, hashlib.sha256(canonical).hexdigest()


def _valid_text(value):
    return (isinstance(value, str) and 0 < len(value.strip()) <= _MAX_TEXT
            and any(char.isalnum() for char in value)
            and not any(ord(char) < 32 and char not in '\n\r\t' for char in value))


def _child_environment():
    env = dict(os.environ)
    for name in ('PYTHONHOME', 'PYTHONPATH'):
        env.pop(name, None)
    env.update(PYTHONNOUSERSITE='1', PYTHONUTF8='1', HF_HUB_OFFLINE='1',
               TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
               DO_NOT_TRACK='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='4', MKL_NUM_THREADS='1')
    return env


def reference_transcript(reference, data, language, existing=''):
    """Return supplied text or a private, versioned local ASR cache entry."""
    if not isinstance(existing, str):
        raise ValueError('Bản chép lời mẫu giọng không hợp lệ.')
    if existing.strip():
        return existing.strip()
    with _lock:
        reference, reference_sha = _reference_metadata(reference)
        data = Path(data).resolve()
        language = _language(language)
        _, record, manifest_sha = _asr_manifest(data)
        identity = {'reference_sha256': reference_sha, 'language': language,
                    'asr_manifest_sha256': manifest_sha, 'asr_revision': record['revision'],
                    'asr_version': record['version']}
        key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode('utf-8')).hexdigest()
        cache = data/'cache/native-transcripts'
        cache.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = cache/(key+'.json')
        try:
            if path.stat().st_size <= 128 * 1024:
                cached = json.loads(path.read_text(encoding='utf-8'))
                if (isinstance(cached, dict) and cached.get('schema') == 1
                        and cached.get('source') == 'local_machine_transcription'
                        and cached.get('local_only') is True
                        and all(cached.get(name) == value for name, value in identity.items())
                        and _valid_text(cached.get('text'))):
                    return cached['text'].strip()
        except (OSError, ValueError, UnicodeError):
            pass
        request = {'reference': str(reference), 'data': str(data), 'language': language,
                   'reference_sha256': reference_sha, 'asr_manifest_sha256': manifest_sha}
        try:
            with (data/'native-transcript.log').open('a', encoding='utf-8') as errors:
                response = subprocess.run([sys.executable, '-s', '-X', 'utf8', str(Path(__file__).resolve()), '--transcribe'],
                    input=json.dumps(request, ensure_ascii=False), stdout=subprocess.PIPE, stderr=errors,
                    text=True, encoding='utf-8', env=_child_environment(), timeout=300, check=False)
        except subprocess.TimeoutExpired:
            raise ValueError('Nhận dạng lời mẫu quá 5 phút. Nhập lời mẫu chính xác rồi thử lại.') from None
        try:
            result = json.loads(response.stdout)
        except (ValueError, TypeError):
            result = None
        if (response.returncode or not isinstance(result, dict) or result.get('ok') is not True
                or result.get('reference_sha256') != reference_sha
                or result.get('asr_manifest_sha256') != manifest_sha
                or result.get('language') != language or not _valid_text(result.get('text'))):
            raise ValueError('Không nhận dạng được lời mẫu chắc chắn. Kiểm tra native-transcript.log hoặc nhập lời mẫu chính xác.')
        if _reference_metadata(reference)[1] != reference_sha:
            raise ValueError('Mẫu giọng đã thay đổi trong lúc nhận dạng; hãy thử lại.')
        text = result['text'].strip()
        write_json_atomic(path, {'schema': 1, 'source': 'local_machine_transcription',
                                'local_only': True, **identity, 'text': text})
        return text


def _transcribe_request(request):
    if not isinstance(request, dict):
        raise ValueError('Yêu cầu nhận dạng ngoại tuyến không hợp lệ.')
    reference, reference_sha = _reference_metadata(request['reference'])
    language = _language(request['language'])
    model, _, manifest_sha = _asr_manifest(request['data'], verify=True)
    if (request.get('reference_sha256') != reference_sha
            or request.get('asr_manifest_sha256') != manifest_sha):
        raise ValueError('Mẫu giọng hoặc mô hình đã thay đổi trước khi nhận dạng.')
    native = Path(os.environ.get('VOICE_STUDIO_NATIVE_ROOT', str(BASE.parent/'runtime-native'))).resolve()
    dependencies = native/'asr'
    if not dependencies.is_dir():
        raise ValueError('Chưa cài thư viện nhận dạng lời mẫu. Chạy TAI_GIONG_DA_NGON_NGU_NHANH.bat.')
    sys.path.insert(0, str(dependencies))
    if importlib.metadata.version('faster-whisper') != ASR_VERSION:
        raise ValueError('Thư viện nhận dạng lời mẫu không đúng phiên bản đã chuẩn bị.')
    from faster_whisper import WhisperModel
    model = WhisperModel(str(model), device='cpu', compute_type='int8',
                         cpu_threads=4, num_workers=1, local_files_only=True)
    segments, _ = model.transcribe(str(reference), language=language, task='transcribe',
                                   beam_size=3, condition_on_previous_text=False,
                                   vad_filter=False, word_timestamps=False)
    pieces = []
    for segment in segments:
        text = segment.text.strip()
        if text and getattr(segment, 'no_speech_prob', 0) > .8 and getattr(segment, 'avg_logprob', 0) < -1:
            raise ValueError('Lời mẫu nhận dạng có độ tin cậy thấp; cần nhập lời mẫu chính xác.')
        if text:
            pieces.append(text)
    text = ' '.join(pieces).strip()
    if not _valid_text(text):
        raise ValueError('Mẫu giọng không có lời đọc nhận dạng được; không tự tạo lời mẫu.')
    return {'ok': True, 'text': text, 'language': language,
            'reference_sha256': reference_sha, 'asr_manifest_sha256': manifest_sha}


def main():
    parser = argparse.ArgumentParser(description='Nhận dạng lời mẫu riêng trên máy, không tải mạng')
    parser.add_argument('--transcribe', action='store_true', required=True)
    parser.parse_args()
    try:
        payload = sys.stdin.read(1024**2 + 1)
        if len(payload) > 1024**2:
            raise ValueError('Yêu cầu nhận dạng lời mẫu quá lớn.')
        request = json.loads(payload)
        with contextlib.redirect_stdout(sys.stderr):
            result = _transcribe_request(request)
        sys.stdout.write(json.dumps(result, ensure_ascii=False)+'\n')
        return 0
    except Exception as exc:
        print('Không nhận dạng xong lời mẫu: '+str(exc), file=sys.stderr, flush=True)
        sys.stdout.write(json.dumps({'ok': False})+'\n')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
