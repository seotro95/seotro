"""Keep the model in memory between jobs; stdout is reserved for the protocol."""
from __future__ import annotations

import contextlib
import json
from pathlib import Path
import sys


def serve():
    for line in sys.stdin:
        try:
            command = json.loads(line)
            folder = Path(command['folder']).resolve()
            if not folder.is_dir() or not (folder / 'input.json').is_file():
                raise ValueError('Không tìm thấy dữ liệu bản đọc đã lưu.')
            # Libraries may print model status or generated text. Keep all of
            # that off the JSON protocol stream, including their first import.
            with contextlib.redirect_stdout(sys.stderr):
                from longform import process_job
                process_job(folder)
            reply = {'ok': True}
        except Exception as exc:
            from cloning_engine import CloningError
            message = str(exc) if isinstance(exc, (CloningError, ValueError)) else 'Bộ máy tạo giọng gặp lỗi. Các đoạn đã lưu được giữ lại để tiếp tục.'
            reply = {'ok': False, 'error': message[:1000]}
        print(json.dumps(reply, ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    if sys.argv[1:] != ['--serve']:
        raise SystemExit('Dùng --serve để khởi động bộ máy tạo giọng.')
    raise SystemExit(serve())
