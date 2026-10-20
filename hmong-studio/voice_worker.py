"""Keep the local model warm in an isolated, cancellable JSON-lines worker.

Standard output and standard error belong to the parent-owned log file. Results
and measured progress use atomic per-job files, never the model's console logs.
"""
import asyncio
import json
import os
from pathlib import Path
import sys
import time
from fastapi import HTTPException
from fastapi.responses import FileResponse


def atomic_json(path, value):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=True), encoding='utf-8')
    # Short-lived progress readers can overlap a replace on Windows.
    for attempt in range(4):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == 3:
                raise
            time.sleep(0.01)


async def main():
    import app
    for line in sys.stdin:
        try:
            request = json.loads(line)
            folder = Path(request['folder'])
            if not folder.is_dir():
                continue
        except (ValueError, TypeError, KeyError):
            # Parent-owned IPC only; never echo malformed requests or user text.
            continue

        def progress(info):
            if not isinstance(info, dict):
                return
            try:
                update = {
                    key: info[key] for key in ('progress', 'phase', 'completed_units',
                                             'total_units', 'generated_seconds') if key in info}
                message = info.get('message')
                if isinstance(message, str) and 0 < len(message) <= 1000:
                    update['message'] = message
                atomic_json(folder / 'progress.json', update)
            except (OSError, TypeError, ValueError):
                # An unavailable progress file must not discard generated audio.
                pass

        try:
            payload = app.Speech.model_validate(request['payload'])
            audio = folder / 'audio.bin'
            response = await app.generate_speech(payload, progress=progress, output_path=audio)
            if isinstance(response, FileResponse):
                if Path(response.path).resolve() != audio.resolve():
                    raise ValueError('unexpected worker audio path')
            else:
                audio.write_bytes(response.body)
            result = {'media_type': response.media_type}
            try:
                engine = getattr(app, 'cosy_engine', None)
                details = engine.availability() if engine is not None else {}
                result['runtime'] = {key: details[key] for key in (
                    'loaded', 'device', 'precision', 'reference_cache_entries', 'compute_mode',
                    'text_embedding_offloaded') if key in details}
            except Exception:
                # Status metadata is optional and must not discard valid audio.
                result['runtime'] = {}
        except HTTPException as exc:
            result = {'error': str(exc.detail)}
        except Exception:
            result = {'error': 'Bộ máy tạo giọng gặp lỗi. Kiểm tra mô hình và cấu hình dịch vụ.'}
        atomic_json(folder / 'result.json', result)
    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
