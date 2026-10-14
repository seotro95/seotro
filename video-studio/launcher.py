"""Local launcher; works from source or a Windows PyInstaller bundle."""
from pathlib import Path
import os
import socket
import sys
import threading
import time
import webbrowser

if getattr(sys, 'frozen', False):
    os.environ.setdefault('VIDEO_STUDIO_DATA', str(Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'VideoStudioVN'))
    # External FFmpeg binaries can live beside the executable.
    os.environ['PATH'] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get('PATH', '')


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--download-worker':
        from download_worker import main as worker
        worker(sys.argv[2], sys.argv[3])
        return
    import uvicorn
    port = int(os.environ.get('VIDEO_STUDIO_PORT', '8766'))
    with socket.socket() as connection:
        if connection.connect_ex(('127.0.0.1', port)) == 0:
            print(f'Cổng {port} đang được sử dụng. Đóng tool cũ hoặc đặt VIDEO_STUDIO_PORT.')
            raise SystemExit(1)
    import app
    def open_browser():
        import urllib.request
        for _ in range(100):
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=1) as response:
                    if response.status == 200:
                        webbrowser.open(f'http://127.0.0.1:{port}')
                        return
            except OSError:
                time.sleep(.1)
    if '--no-browser' not in sys.argv:
        threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app.app, host='127.0.0.1', port=port, access_log=False)


if __name__ == '__main__':
    main()
