"""Open the local reader after its loopback HTTP server is ready."""
import argparse
import os
from pathlib import Path
import socket
import threading
import time
import urllib.request
import webbrowser

BASE = Path(__file__).resolve().parent
data = Path(os.environ.setdefault('HMONG_STUDIO_DATA_DIR', str(BASE.parent / '.data')))
for name, folder in (('MPLCONFIGDIR', 'matplotlib'), ('XDG_CACHE_HOME', 'xdg'),
                     ('NUMBA_CACHE_DIR', 'numba'), ('HF_HOME', 'huggingface')):
    target = data / 'cache' / folder
    target.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault(name, str(target))
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ.setdefault('OMP_NUM_THREADS', '4')


def open_when_ready(url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(60):
        try:
            with opener.open(url + '/api/status', timeout=1):
                pass
            webbrowser.open(url)
            return
        except OSError:
            time.sleep(.5)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Mo Hmong Nhanh tren may nay.')
    device = parser.add_mutually_exclusive_group()
    device.add_argument('--cpu', action='store_true', help='Tao giong bang CPU.')
    device.add_argument('--gpu', action='store_true', help='Uu tien GPU sau khi bo cai da kiem tra CUDA.')
    args = parser.parse_args(argv)
    if args.cpu:
        os.environ['HMONG_F5_DEVICE'] = 'cpu'
    elif args.gpu:
        os.environ['HMONG_F5_DEVICE'] = 'auto'
    import uvicorn
    from app import app
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen(128)
        url = f'http://127.0.0.1:{listener.getsockname()[1]}'
        print('Hmong Nhanh: ' + url, flush=True)
        print('Giu cua so nay mo trong khi dung. Nhan Ctrl+C de tat.', flush=True)
        threading.Thread(target=open_when_ready, args=(url,), daemon=True).start()
        server = uvicorn.Server(uvicorn.Config(app, log_level='warning', access_log=False))
        server.run(sockets=[listener])


if __name__ == '__main__':
    main()
