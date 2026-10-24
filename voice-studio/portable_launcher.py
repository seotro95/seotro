"""Open this data directory's running studio, or start one local server."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import webbrowser

from hmong_assets import active_engine as active_hmong_engine
from runtime_instance import StartupLock, discover_instance, legacy_discover
from studio_variant import DEFAULT_DATA_FOLDER, IS_HMONG


def available_port():
    for port in range(8770, 8790):
        with socket.socket() as sock:
            try:
                sock.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    raise RuntimeError('Cong 8770-8789 dang ban. Dong studio cu roi mo lai.')


def _existing_studio(data, root):
    return discover_instance(data, root) or legacy_discover(data, root)


def _open_browser(url, version, enabled):
    try:
        if enabled and not webbrowser.open(url + '/?v=' + str(version)):
            print('Khong tu mo duoc trinh duyet. Mo dia chi Studio ben tren.', flush=True)
    except webbrowser.Error:
        print('Khong tu mo duoc trinh duyet. Mo dia chi Studio ben tren.', flush=True)


def _reuse(studio, expected_backend, open_browser):
    print('REUSED: existing Voice Studio', flush=True)
    if studio.get('backend') != expected_backend:
        print(f'NOTICE: Studio dang chay backend {studio.get("backend", "unknown")}; '
              f'launcher yeu cau {expected_backend}. Giu backend dang chay. '
              'Dong studio cu truoc khi doi backend.', flush=True)
    print(f'Studio: {studio["url"]}', flush=True)
    _open_browser(studio['url'], studio.get('version', ''), open_browser)
    return 0


def main(open_browser=True):
    root = Path(__file__).resolve().parent
    data = Path(os.environ.get('VOICE_STUDIO_DATA_DIR', str(root / DEFAULT_DATA_FOLDER))).resolve()
    expected_backend = active_hmong_engine() if IS_HMONG else 'standard'
    print(f'Dang mo Voice Studio. Du lieu: {data}', flush=True)
    process = None
    try:
        reused = None
        # A second launcher must wait until the first has published a ready,
        # verified server. This lock does not own the server's lifetime.
        with StartupLock(data):
            reused = _existing_studio(data, root)
            if reused is None:
                port = available_port()
                url = f'http://127.0.0.1:{port}'
                child_env = os.environ.copy()
                child_env['VOICE_STUDIO_DATA_DIR'] = str(data)
                child_env['VOICE_STUDIO_URL'] = url
                process = subprocess.Popen(
                    [sys.executable, '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1',
                     '--port', str(port), '--no-access-log', '--no-use-colors'], cwd=root, env=child_env)
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        # An older launcher may not use the startup lock. If its
                        # server won the data lock, reopen that proven instance.
                        reused = _existing_studio(data, root)
                        if reused is not None:
                            break
                        raise RuntimeError('Khong mo duoc studio. Xem thong bao loi ben tren.')
                    studio = discover_instance(data, root)
                    if studio and studio['pid'] == process.pid and studio['url'] == url:
                        # Verified /api/runtime identity proves ASGI startup is
                        # complete. /api/config can hash gigabytes of models on
                        # filesystems where integrity caching is unavailable.
                        studio_version = studio.get('version', '')
                        break
                    time.sleep(.25)
                else:
                    raise RuntimeError('Studio chua san sang sau 60 giay.')
        if reused is not None:
            return _reuse(reused, expected_backend, open_browser)
        print(f'Studio: {url}\nGiu cua so nay mo. Bam Ctrl+C de tat.', flush=True)
        _open_browser(url, studio_version, open_browser)
        returncode = process.wait()
        if returncode != 0:
            raise RuntimeError(f'Studio da dung voi ma loi {returncode}. Xem thong bao loi ben tren.')
    except KeyboardInterrupt:
        pass
    finally:
        if process is not None and process.poll() is None:
            try:
                process.wait(timeout=8)  # Ctrl+C is delivered to the console group.
            except subprocess.TimeoutExpired:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                else:
                    process.terminate()
                process.wait(timeout=10)
    return 0


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'LOI: {exc}', flush=True)
        sys.exit(1)
