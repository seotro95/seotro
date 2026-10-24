"""One cancellable inference process for each requested recording."""
import asyncio
import json
from pathlib import Path
import sys
from fastapi import HTTPException


async def main():
    import app
    folder = Path(sys.argv[1])
    try:
        raw = json.load(sys.stdin)
        payload = app.Speech.model_validate(raw)
        reference = raw['_reference']
        response = await app.synthesize_reference(payload, Path(reference['path']), reference['text'])
        (folder / 'audio.bin').write_bytes(response.body)
        result = {'media_type': 'audio/wav'}
    except HTTPException as exc:
        result = {'error': str(exc.detail)}
    except Exception:
        result = {'error': 'Không tạo được giọng. Kiểm tra mô hình và dung lượng RAM.'}
    (folder / 'result.json').write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
    return 1 if 'error' in result else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
