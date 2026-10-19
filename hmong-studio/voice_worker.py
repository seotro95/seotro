"""Run inference in an isolated, cancellable process; never log input or keys."""
import asyncio
import json
from pathlib import Path
import sys
from fastapi import HTTPException

async def main():
    import app
    folder = Path(sys.argv[1])
    try:
        payload = app.Speech.model_validate(json.load(sys.stdin))
        response = await app.speech(payload)
        (folder / 'audio.bin').write_bytes(response.body)
        result = {'media_type': response.media_type}
    except HTTPException as exc:
        result = {'error': str(exc.detail)}
    except Exception:
        result = {'error': 'Bộ máy tạo giọng gặp lỗi. Kiểm tra mô hình và cấu hình dịch vụ.'}
    (folder / 'result.json').write_text(json.dumps(result), encoding='utf-8')
    return 1 if 'error' in result else 0

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
