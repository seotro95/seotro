"""CPU models: automatic first-use download, then inference without network calls."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
from urllib.parse import urlsplit
import wave
import zipfile
import httpx

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('VIDEO_STUDIO_DATA', str(ROOT / 'data'))).expanduser().resolve()
MODELS = DATA / 'models'
MODELS.mkdir(parents=True, exist_ok=True)
LANGUAGES = {'vi':'Tiếng Việt','en':'Tiếng Anh','zh':'Tiếng Trung','ja':'Tiếng Nhật',
             'ko':'Tiếng Hàn','th':'Tiếng Thái','fr':'Tiếng Pháp','de':'Tiếng Đức','es':'Tiếng Tây Ban Nha','ru':'Tiếng Nga'}
VOICES = {
    'vi_VN-vais1000-medium': {'name':'Tiếng Việt — VAIS', 'language':'vi', 'path':'vi/vi_VN/vais1000/medium'},
    'en_US-lessac-medium': {'name':'Tiếng Anh — Lessac', 'language':'en', 'path':'en/en_US/lessac/medium'},
}
PIPER_REVISION = 'c10ece1aade47bb51c153c893d14e5bf8e5b7117'
ARGOS_INDEX = 'https://raw.githubusercontent.com/argosopentech/argospm-index/main/index.json'


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url, target, *, expected_hash=None, max_bytes=1024 ** 3, progress=None):
    """TLS-verified, bounded download with atomic publication; no partial cached models."""
    if urlsplit(url).scheme != 'https':
        raise ValueError('Nguồn model cần dùng HTTPS.')
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + '.part')
    try:
        with httpx.Client(follow_redirects=True, timeout=httpx.Timeout(60, connect=20), headers={'Accept-Encoding':'identity'}) as client:
            with client.stream('GET', url) as response:
                response.raise_for_status()
                count, digest = 0, hashlib.sha256()
                declared = int(response.headers.get('content-length') or 0)
                if declared > max_bytes:
                    raise ValueError('Model vượt giới hạn tải cho phép.')
                with temp.open('wb') as out:
                    for chunk in response.iter_bytes(1024 * 1024):
                        count += len(chunk)
                        if count > max_bytes:
                            raise ValueError('Model vượt giới hạn tải cho phép.')
                        digest.update(chunk)
                        out.write(chunk)
                        if progress and declared:
                            progress(10 + int(35 * count / declared))
                if not count or (declared and count != declared):
                    raise ValueError('Tệp tải chưa đầy đủ. Hãy kiểm tra Internet rồi thử lại.')
                if expected_hash and digest.hexdigest() != expected_hash:
                    raise ValueError('Checksum model không khớp. Tệp chưa được sử dụng.')
        os.replace(temp, target)
    except httpx.HTTPError:
        raise ValueError('Không tải được model. Cần Internet cho lần dùng đầu; model đã cài vẫn dùng được offline.') from None
    finally:
        temp.unlink(missing_ok=True)


def json_url(url):
    try:
        with httpx.Client(follow_redirects=True, timeout=30) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, json.JSONDecodeError):
        raise ValueError('Không đọc được danh mục model. Kiểm tra Internet rồi thử lại.') from None


def pair_path(source, target):
    return MODELS / 'translation' / (source + '_' + target)


def has_pair(source, target):
    root = pair_path(source, target)
    return (root / 'model' / 'model.bin').is_file() and (root / 'sentencepiece.model').is_file() and (root / 'metadata.json').is_file()


def translation_index():
    path = MODELS / 'translation-index.json'
    # Existing installed models never consult this online index during inference.
    if path.exists() and time.time() - path.stat().st_mtime < 7 * 86400:
        return json.loads(path.read_text(encoding='utf-8'))
    try:
        index = json_url(ARGOS_INDEX)
        if not isinstance(index, list):
            raise ValueError('Danh mục model dịch không hợp lệ.')
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(index), encoding='utf-8')
        os.replace(temporary, path)
        return index
    except ValueError:
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
        raise


def install_pair(source, target, progress=None):
    from filelock import FileLock
    path = pair_path(source, target)
    with FileLock(str(MODELS / f'translate-{source}-{target}.lock'), timeout=600):
        if has_pair(source, target):
            return path
        matches = [p for p in translation_index() if p.get('from_code') == source and p.get('to_code') == target]
        if not matches:
            raise ValueError(f'Chưa có model dịch {source} → {target}. Chọn ngôn ngữ khác.')
        from packaging.version import Version
        package = max(matches, key=lambda p: Version(p['package_version']))
        url = package['links'][0]
        host = (urlsplit(url).hostname or '').lower()
        if host not in ('argos-net.com', 'downloads.argosopentech.com', 'argosopentech.nyc3.digitaloceanspaces.com'):
            raise ValueError('Nguồn model dịch chưa được hỗ trợ; cần bản cập nhật tool.')
        archive = MODELS / f'{source}-{target}.argosmodel'
        fetch(url, archive, progress=progress, expected_hash=package.get('sha256'))
        with tempfile.TemporaryDirectory(dir=MODELS) as scratch:
            scratch = Path(scratch)
            with zipfile.ZipFile(archive) as bundle:
                if bundle.testzip() is not None:
                    raise ValueError('Gói model dịch bị lỗi.')
                if sum(e.file_size for e in bundle.infolist()) > 2 * 1024 ** 3:
                    raise ValueError('Gói model dịch quá lớn.')
                for entry in bundle.infolist():
                    resolved = (scratch / entry.filename).resolve()
                    if not resolved.is_relative_to(scratch.resolve()) or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                        raise ValueError('Gói model có đường dẫn không hợp lệ.')
                bundle.extractall(scratch)
            candidates = [p.parent for p in scratch.rglob('metadata.json') if (p.parent / 'model' / 'model.bin').is_file() and (p.parent / 'sentencepiece.model').is_file()]
            if len(candidates) != 1:
                raise ValueError('Không tìm thấy model SentencePiece/CTranslate2 trong gói.')
            metadata = json.loads((candidates[0] / 'metadata.json').read_text())
            if metadata.get('from_code') != source or metadata.get('to_code') != target:
                raise ValueError('Ngôn ngữ model không khớp.')
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                raise ValueError('Model cũ chưa đầy đủ. Hãy đổi tên thư mục model lỗi rồi thử lại.')
            shutil.move(str(candidates[0]), str(path))
        archive.unlink(missing_ok=True)
        return path


def translation_route(source, target):
    if source == target:
        return []
    if has_pair(source, target):
        return [(source, target)]
    if source != 'en' and target != 'en' and has_pair(source, 'en') and has_pair('en', target):
        return [(source, 'en'), ('en', target)]
    index = translation_index()
    pairs = {(p.get('from_code'), p.get('to_code')) for p in index}
    if (source, target) in pairs:
        return [(source, target)]
    if (source, 'en') in pairs and ('en', target) in pairs:
        return [(source, 'en'), ('en', target)]
    raise ValueError('Chưa có lộ trình model dịch giữa hai ngôn ngữ đã chọn.')


def detect_language(text):
    from langdetect import DetectorFactory, detect, LangDetectException
    DetectorFactory.seed = 0
    try:
        code = detect(text[:20000])
    except LangDetectException:
        raise ValueError('Không nhận dạng được ngôn ngữ. Hãy chọn ngôn ngữ nguồn.') from None
    code = {'zh-cn':'zh','zh-tw':'zh'}.get(code, code)
    if code not in LANGUAGES:
        raise ValueError('Ngôn ngữ tự nhận dạng chưa được hỗ trợ. Hãy chọn ngôn ngữ nguồn.')
    return code


def translate_cues(cues, source, target, progress=None):
    import ctranslate2
    import sentencepiece
    source = detect_language(' '.join(c['text'] for c in cues)) if source == 'auto' else source
    route = translation_route(source, target)
    result = [dict(cue) for cue in cues]
    for route_number, (a, b) in enumerate(route):
        root = install_pair(a, b, progress)
        tokenizer = sentencepiece.SentencePieceProcessor(model_file=str(root / 'sentencepiece.model'))
        translator = ctranslate2.Translator(str(root / 'model'), device='cpu', compute_type='int8', inter_threads=1, intra_threads=2)
        metadata = json.loads((root / 'metadata.json').read_text())
        prefix = metadata.get('target_prefix', '')
        for i, cue in enumerate(result):
            tokens = tokenizer.encode(cue['text'].replace('\n', ' '), out_type=str)
            chunks = [tokens[offset:offset + 256] for offset in range(0, len(tokens), 256)]
            translations = translator.translate_batch(chunks, beam_size=4, replace_unknowns=True,
                    max_decoding_length=1024, length_penalty=.2,
                    target_prefix=[[prefix]] * len(chunks) if prefix else None)
            text = ' '.join(tokenizer.decode(r.hypotheses[0]).replace('▁', ' ') for r in translations).strip()
            if prefix and text.startswith(prefix):
                text = text[len(prefix):].strip()
            if not text or '-->' in text:
                raise ValueError('Model dịch trả đoạn không hợp lệ. Phụ đề gốc được giữ nguyên.')
            cue['text'] = text
            if progress:
                progress(50 + int(40 * (route_number + (i + 1) / len(cues)) / len(route)))
        del translator
    return result


def piper_model(voice, progress=None):
    from filelock import FileLock
    if voice not in VOICES:
        raise ValueError('Giọng đọc chưa được hỗ trợ.')
    root = MODELS / 'voices' / voice
    root.mkdir(parents=True, exist_ok=True)
    model = root / (voice + '.onnx')
    manifest = root / 'verified.json'
    with FileLock(str(root / 'download.lock'), timeout=600):
        if manifest.exists():
            hashes = json.loads(manifest.read_text())
            if all((root / name).is_file() and file_hash(root / name) == digest for name, digest in hashes.items()):
                return model
            raise ValueError('Model giọng đọc đã thay đổi hoặc bị hỏng. Xóa thư mục model lỗi để tải lại.')
        base = 'https://huggingface.co/rhasspy/piper-voices/resolve/' + PIPER_REVISION + '/' + VOICES[voice]['path'] + '/'
        # LFS SHA256 is fetched from the authoritative model metadata, not the CDN ETag.
        metadata = json_url('https://huggingface.co/api/models/rhasspy/piper-voices/revision/' + PIPER_REVISION + '?blobs=true')
        relative = VOICES[voice]['path'] + '/' + voice + '.onnx'
        item = next((f for f in metadata.get('siblings', []) if f['rfilename'] == relative), None)
        digest = (item or {}).get('lfs', {}).get('sha256')
        if not digest or not re.fullmatch(r'[a-f0-9]{64}', digest):
            raise ValueError('Không đọc được checksum chính thức của model giọng đọc.')
        fetch(base + voice + '.onnx', model, expected_hash=digest, progress=progress)
        config = root / (voice + '.onnx.json')
        fetch(base + config.name, config, max_bytes=1024 ** 2)
        json.loads(config.read_text())
        fetch(base + 'MODEL_CARD', root / 'MODEL_CARD', max_bytes=1024 ** 2)
        manifest.write_text(json.dumps({p.name:file_hash(p) for p in (model, config, root / 'MODEL_CARD')}), encoding='utf-8')
        return model


def speak(text, voice, output, speed=1, progress=None):
    import onnxruntime
    onnxruntime.disable_telemetry_events()
    from piper import PiperVoice
    from piper.config import SynthesisConfig
    model = piper_model(voice, progress)
    synthesizer = PiperVoice.load(str(model), use_cuda=False)
    with wave.open(str(output), 'wb') as audio:
        synthesizer.synthesize_wav(text, audio, syn_config=SynthesisConfig(length_scale=1 / speed))


def whisper_model(name='tiny'):
    # Configure supported cache locations before Hugging Face initializes them.
    os.environ.setdefault('HF_HOME', str(MODELS / 'huggingface'))
    os.environ.setdefault('HF_XET_CACHE', str(MODELS / 'huggingface' / 'xet'))
    from faster_whisper import WhisperModel
    cache = MODELS / 'whisper'
    try:
        return WhisperModel(name, device='cpu', compute_type='int8', cpu_threads=2, num_workers=1,
                            download_root=str(cache), local_files_only=True)
    except (ValueError, OSError):
        return WhisperModel(name, device='cpu', compute_type='int8', cpu_threads=2, num_workers=1,
                            download_root=str(cache))


def status():
    import importlib.util
    return {'languages':LANGUAGES, 'voices':[{'id':v, **metadata,
            'installed':(MODELS / 'voices' / v / 'verified.json').is_file()} for v, metadata in VOICES.items()],
            'installed_pairs':[{'source':a,'target':b} for a in LANGUAGES for b in LANGUAGES if has_pair(a,b)],
            'translation': all(importlib.util.find_spec(p) for p in ('ctranslate2','sentencepiece')),
            'piper': importlib.util.find_spec('piper') is not None,
            'whisper': importlib.util.find_spec('faster_whisper') is not None,
            'whisper_downloaded': (MODELS / 'whisper').exists() and any((MODELS / 'whisper').rglob('model.bin'))}
