"""Start the editor with standard Python; AI dependencies are optional at boot."""
import argparse
import os
from pathlib import Path
import sys
import threading
import webbrowser

BASE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description='Hmoob VoiceLab — Hmong Trắng, văn bản dài')
    parser.add_argument('--port', type=int, default=8123)
    parser.add_argument('--data-dir', type=Path, default=Path(os.getenv('HMOOB_DATA_DIR', BASE / '.data')))
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error('Cổng phải nằm trong 0–65535.')
    os.environ['HMOOB_DATA_DIR'] = str(args.data_dir.resolve())
    from server import make_server
    try:
        server = make_server(args.data_dir, port=args.port)
    except (ValueError, OSError) as exc:
        raise SystemExit('Không khởi động được: ' + str(exc)) from None
    url = f'http://127.0.0.1:{server.server_port}'
    print('Hmoob VoiceLab 1.0 · ' + url, flush=True)
    print('Dừng bằng Ctrl+C. Tác vụ chưa xong có thể tiếp tục ở lần mở sau.', flush=True)
    if not args.no_browser:
        threading.Timer(.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.manager.close()
        server.server_close()


if __name__ == '__main__':
    if sys.version_info < (3, 10):
        raise SystemExit('Cần Python 3.10 trở lên; AI dùng Python 3.10–3.12 64-bit.')
    main()
