"""Open only the standalone voice application and clean up its own server."""
import argparse
import json
import os
from pathlib import Path
import signal
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
    raise RuntimeError('Cong 8770-8789 dang ban. Dong tool cu roi mo lai.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browser', action='store_true', help='Start without automatically opening a browser')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    port = available_port()
    url = f'http://127.0.0.1:{port}'
    command = [sys.executable, '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1',
               '--port', str(port), '--no-access-log']
    options = {} if os.name == 'nt' else {'start_new_session': True}
    process = subprocess.Popen(command, cwd=root, **options)

    def interrupted(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(240):
            if process.poll() is not None:
                raise RuntimeError('Khong mo duoc tool. Kiem tra loi trong cua so nay.')
            try:
                with opener.open(url + '/api/config', timeout=1) as response:
                    config = json.load(response)
                if config.get('edition') == 'standalone-voice':
                    break
            except (OSError, ValueError):
                pass
            time.sleep(.25)
        else:
            raise RuntimeError('Tool chua san sang sau 60 giay.')
        print('Voice Studio Rieng da mo. Giu cua so nay mo; Ctrl+C de tat.', flush=True)
        print('Du lieu va ban thu: ' + str(root / '.data'), flush=True)
        if not args.no_browser:
            webbrowser.open(url + '/?v=' + config['version'])
        process.wait()
    except KeyboardInterrupt:
        pass
    finally:
        if process.poll() is None:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            else:
                os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('LOI: ' + str(exc), file=sys.stderr, flush=True)
        sys.exit(1)
