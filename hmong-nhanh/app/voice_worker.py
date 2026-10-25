"""Keep the model in memory between jobs; stdout is reserved for the protocol."""
from __future__ import annotations

import contextlib
import json
from pathlib import Path
import sys
import traceback


def serve():
    # The parent writes UTF-8 regardless of the Windows console code page.
    # Decode its bytes explicitly; stdout replies use ASCII JSON escapes so a
    # launch outside the BAT also handles Vietnamese folder names and errors.
    source = getattr(sys.stdin, 'buffer', sys.stdin)
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
    for line in source:
        try:
            if isinstance(line, bytes):
                line = line.decode('utf-8')
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
            if not isinstance(exc, (CloningError, ValueError)):
                try:
                    sys.stderr.write('Voice worker failure: ' + type(exc).__name__ + '\n' +
                                     ''.join(traceback.format_tb(exc.__traceback__, limit=8)))
                    sys.stderr.flush()
                except (OSError, UnicodeError):
                    pass
            message = str(exc) if isinstance(exc, (CloningError, ValueError)) else 'Bộ máy tạo giọng gặp lỗi. Các đoạn đã lưu được giữ lại để tiếp tục.'
            reply = {'ok': False, 'error': message[:1000]}
        print(json.dumps(reply, ensure_ascii=True), flush=True)
    return 0


if __name__ == '__main__':
    if sys.argv[1:] != ['--serve']:
        raise SystemExit('Dùng --serve để khởi động bộ máy tạo giọng.')
    raise SystemExit(serve())
