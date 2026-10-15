"""Open the bundled Windows app without system Python, pip or FFmpeg setup."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser


def available_port():
    for port in range(8770, 8790):
        with socket.socket() as sock:
            try:
                sock.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    raise RuntimeError('Cong 8770-8789 dang ban. Dong studio cu roi mo lai.')


def main():
    root = Path(__file__).resolve().parent
    port = available_port()
    url = f'http://127.0.0.1:{port}'
    print('Dang mo Voice Studio. Du lieu duoc luu trong voice-studio/.data.', flush=True)
    process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', str(port), '--no-access-log'], cwd=root)
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(240):
            if process.poll() is not None:
                raise RuntimeError('Khong mo duoc studio. Xem thong bao loi ben tren.')
            try:
                with opener.open(url+'/api/config', timeout=1) as response:
                    if json.load(response).get('mode') == 'local':
                        break
            except (OSError, ValueError):
                time.sleep(.25)
        else:
            raise RuntimeError('Studio chua san sang sau 60 giay.')
        print(f'Studio: {url}\nGiu cua so nay mo. Bam Ctrl+C de tat.', flush=True)
        webbrowser.open(url)
        process.wait()
    except KeyboardInterrupt:
        pass
    finally:
        if process.poll() is None:
            try:
                process.wait(timeout=8)  # Ctrl+C is delivered to the console group.
            except subprocess.TimeoutExpired:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                else:
                    process.terminate()
                process.wait(timeout=10)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'LOI: {exc}', flush=True)
        sys.exit(1)
