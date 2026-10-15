"""One CPU process per task, so downloads and inference can be cancelled."""
import json
from pathlib import Path
import re
import sys
from offline_models import LANGUAGES, install_pair, piper_model, speak, translate_cues, whisper_model
from subtitles import parse_srt, to_srt


def run(payload, folder):
    def progress(percent):
        temporary = folder / 'progress.tmp'
        temporary.write_text(json.dumps({'progress':percent}), encoding='utf-8')
        temporary.replace(folder / 'progress.json')
    action = payload['action']
    if action == 'translate':
        cues = parse_srt(Path(payload['source']).read_text(encoding='utf-8-sig'))
        translated = translate_cues(cues, payload['source_language'], payload['language'], progress)
        (folder / 'phu_de_dich.srt').write_text(to_srt(translated), encoding='utf-8')
    elif action == 'tts':
        if payload.get('provider', 'piper') == 'edge':
            from online_services import speak_edge
            speak_edge(payload['text'], payload['voice'], folder / 'giong_doc.mp3', payload['speed'])
        else:
            speak(payload['text'], payload['voice'], folder / 'giong_doc.wav', payload['speed'], progress)
    elif action == 'stt':
        model = whisper_model(payload['model'])
        progress(45)
        segments, info = model.transcribe(payload['source'], language=payload['language'] or None,
                                         vad_filter=True, beam_size=5)
        cues = []
        for segment in segments:
            if segment.text.strip() and segment.end > segment.start:
                cues.append({'start':max(0,segment.start),'end':segment.end,'text':segment.text.strip()})
            progress(45 + int(45 * min(segment.end / max(info.duration, .1), 1)))
        if not cues:
            raise ValueError('Không phát hiện lời nói trong tệp.')
        (folder / 'phu_de.srt').write_text(to_srt(cues), encoding='utf-8')
    elif action == 'prepare':
        piper_model('vi_VN-vais1000-medium', progress)
        whisper_model('tiny')
        install_pair('en', 'vi', progress)
        (folder / 'model_san_sang.txt').write_text('Đã chuẩn bị giọng Việt, Whisper Tiny và dịch Anh → Việt. Có thể dùng các model này offline.', encoding='utf-8')
    else:
        raise ValueError('Tác vụ cục bộ không hợp lệ.')
    progress(95)


def main(payload_path):
    payload_path = Path(payload_path)
    try:
        run(json.loads(payload_path.read_text(encoding='utf-8')), payload_path.parent)
    except Exception as exc:
        message = str(exc) if isinstance(exc, ValueError) else 'Engine cục bộ không xử lý được. Kiểm tra Internet khi tải model và bộ nhớ của máy.'
        (payload_path.parent / 'error.json').write_text(json.dumps({'message':message[:1200]}, ensure_ascii=False), encoding='utf-8')
        raise SystemExit(1)


if __name__ == '__main__':
    main(sys.argv[1])
