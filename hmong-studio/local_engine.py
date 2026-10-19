"""Optional local inference. Never substitute another language for Hmong."""
from __future__ import annotations

import importlib.util
import io
import os
import re
import shutil
import subprocess
import threading
import wave

LANGUAGES = {'mww': 'Hmong Trắng', 'vi': 'Tiếng Việt', 'en': 'English'}
ASR_CODES = {'mww': 'hmn', 'vi': 'vie', 'en': 'eng'}
_lock = threading.Lock()
_tts = None
_asr = None


class EngineError(Exception):
    pass


def tts_model(language):
    # Hmong model/dialect must be explicitly selected after verification.
    return os.getenv('HMONG_LOCAL_TTS_MODEL' if language == 'mww' else
                     f'STUDIO_TTS_MODEL_{language.upper()}',
                     '' if language == 'mww' else f'facebook/mms-tts-{ASR_CODES[language]}')


def availability():
    return {'dependencies': all(importlib.util.find_spec(x) is not None for x in ('torch', 'transformers', 'numpy')),
            'ffmpeg': bool(shutil.which('ffmpeg')),
            'tts_models': {code: bool(tts_model(code)) for code in LANGUAGES},
            'asr_model': os.getenv('HMONG_LOCAL_ASR_MODEL', 'facebook/mms-1b-all'),
            'hmong_asr_code': os.getenv('HMONG_ASR_CODE', 'hmn')}


def _libraries():
    try:
        import numpy as np
        import torch
        import transformers
        return np, torch, transformers
    except ImportError as exc:
        raise EngineError('Chưa cài bộ AI cục bộ. Chạy install_local_ai.bat rồi khởi động lại tool.') from exc


def _wav(samples, rate):
    np, _, _ = _libraries()
    samples = np.asarray(samples).reshape(-1)
    if not samples.size or not np.isfinite(samples).all() or np.max(np.abs(samples)) < 1e-6:
        raise EngineError('Mô hình tạo âm thanh rỗng hoặc không hợp lệ; chưa có bản đọc hoàn tất.')
    out = io.BytesIO()
    with wave.open(out, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes((np.clip(samples, -1, 1) * 32767).astype('<i2').tobytes())
    return out.getvalue()


def synthesize(text, language, speed, voice, emotion):
    global _tts
    if voice != 'model-default' or emotion != 'neutral':
        raise EngineError('MMS chỉ có giọng gốc, không hỗ trợ nhân bản mẫu nam/nữ hoặc cảm xúc. Chọn Giọng gốc và Tự nhiên, hoặc dùng dịch vụ có hỗ trợ các tính năng này.')
    model_id = tts_model(language)
    if not model_id:
        raise EngineError('Chưa có mô hình TTS Hmong Trắng được xác minh. Thiết lập HMONG_LOCAL_TTS_MODEL tới mô hình VITS hỗ trợ đúng Hmong Trắng; không thể dùng mẫu MP3 thay mô hình.')
    np, torch, transformers = _libraries()
    if len(text) > 2000:
        raise EngineError('Chế độ AI cục bộ nhận tối đa 2.000 ký tự mỗi lượt. Chia kịch bản thành các phần nhỏ.')
    if not _lock.acquire(blocking=False):
        raise EngineError('AI cục bộ đang xử lý tác vụ khác. Hãy chờ hoàn tất.')
    try:
        if _tts is None or _tts[0] != model_id:
            tokenizer = transformers.AutoTokenizer.from_pretrained(model_id, trust_remote_code=False)
            model = transformers.VitsModel.from_pretrained(model_id, trust_remote_code=False).eval()
            _tts = (model_id, tokenizer, model)
        _, tokenizer, model = _tts
        parts = []
        # Bound sentence sizes to avoid huge attention matrices on CPU.
        for sentence in re.split(r'(?<=[.!?;])\s+|\n+', text.strip()):
            words = sentence.split()
            while words:
                chunk = []
                while words and (not chunk or len(' '.join(chunk + words[:1])) <= 220):
                    chunk.append(words.pop(0))
                inputs = tokenizer(' '.join(chunk), return_tensors='pt')
                if tokenizer.unk_token_id is not None and (inputs['input_ids'] == tokenizer.unk_token_id).any():
                    raise EngineError('Mô hình không nhận được một số ký tự của lời đọc. Kiểm tra ngôn ngữ/mô hình.')
                model.speaking_rate = speed
                with torch.inference_mode():
                    sound = model(**inputs).waveform[0].cpu().numpy()
                parts.extend([sound, np.zeros(int(model.config.sampling_rate * .15), dtype=np.float32)])
        if not parts:
            raise EngineError('Không có lời để đọc.')
        return _wav(np.concatenate(parts), model.config.sampling_rate)
    except EngineError:
        raise
    except Exception as exc:
        raise EngineError('Không nạp/chạy được mô hình TTS. Kiểm tra mã mô hình, dung lượng RAM và quyền tải từ Hugging Face; hoặc dùng thư mục mô hình đã tải trên máy.') from exc
    finally:
        _lock.release()


def transcribe(audio, language):
    global _asr
    np, torch, transformers = _libraries()
    if not shutil.which('ffmpeg'):
        raise EngineError('Chưa có FFmpeg trong PATH. Cài FFmpeg rồi mở lại tool.')
    try:
        result = subprocess.run(['ffmpeg', '-v', 'error', '-protocol_whitelist', 'pipe', '-i', 'pipe:0', '-t', '601', '-f', 'f32le',
                                 '-ac', '1', '-ar', '16000', 'pipe:1'], input=audio,
                                capture_output=True, timeout=90, check=True)
    except (subprocess.SubprocessError, OSError) as exc:
        raise EngineError('Không giải mã được âm thanh. Thử tệp WAV/MP3 hợp lệ, tối đa 10 phút.') from exc
    samples = np.frombuffer(result.stdout, dtype='<f4').copy()
    if not samples.size or len(samples) > 600 * 16000 or not np.isfinite(samples).all():
        raise EngineError('Âm thanh phải có nội dung và dài tối đa 10 phút.')
    model_id = os.getenv('HMONG_LOCAL_ASR_MODEL', 'facebook/mms-1b-all')
    code = os.getenv('HMONG_ASR_CODE', 'hmn') if language == 'mww' else ASR_CODES[language]
    if not _lock.acquire(blocking=False):
        raise EngineError('AI cục bộ đang xử lý tác vụ khác. Hãy chờ hoàn tất.')
    try:
        if _asr is None or _asr[0:2] != (model_id, code):
            processor = transformers.AutoProcessor.from_pretrained(model_id, target_lang=code, trust_remote_code=False)
            model = transformers.Wav2Vec2ForCTC.from_pretrained(model_id, target_lang=code,
                       ignore_mismatched_sizes=True, trust_remote_code=False).eval()
            _asr = (model_id, code, processor, model)
        _, _, processor, model = _asr
        # Non-overlapping 20s windows keep memory bounded. Boundary words may require correction.
        lines = []
        for start in range(0, len(samples), 20 * 16000):
            inputs = processor(samples[start:start+20*16000], sampling_rate=16000, return_tensors='pt', padding=True)
            with torch.inference_mode():
                logits = model(**inputs).logits
            line = processor.batch_decode(torch.argmax(logits, dim=-1))[0].strip()
            if line:
                lines.append(line)
        if not lines:
            raise EngineError('Mô hình chưa nhận dạng được lời. Thử âm thanh rõ, ít tạp âm và kiểm tra đúng ngôn ngữ.')
        return '\n'.join(lines)
    except EngineError:
        raise
    except Exception as exc:
        raise EngineError('Không nạp/chạy được mô hình ASR cho ngôn ngữ đã chọn. Mã Hmong hmn cần có trong mô hình và cần người bản ngữ kiểm chứng; kiểm tra quyền tải mô hình/mã adapter.') from exc
    finally:
        _lock.release()
