"""Install clone dependencies without mutating an environment used by Studio."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import uuid
import venv

from setup_venv import supported

BASE = Path(__file__).resolve().parent
SCHEMA = 1
TORCH = ['torch==2.6.0', 'torchaudio==2.6.0']
ENVIRONMENT = re.compile(r'\.venv-clone-[0-9a-f]{12}')


def dependency_fingerprint(root):
    digest = hashlib.sha256(b'hmong-clone-cpu-runtime-v1\0')
    for name in ('requirements.txt', 'requirements-cosy.txt'):
        digest.update(name.encode() + b'\0' + (Path(root) / name).read_bytes())
    digest.update(json.dumps(TORCH).encode())
    return digest.hexdigest()


def _paths(root):
    folder = Path(root).resolve() / '.data' / 'runtime'
    folder.mkdir(parents=True, exist_ok=True)
    return folder, folder / 'clone-runtime.json'


def _atomic_json(path, value):
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     prefix=path.name + '-', suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, ensure_ascii=False, indent=2)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def installer_lock(root):
    folder, _ = _paths(root)
    with (folder / 'clone-install.lock').open('a+b') as handle:
        handle.seek(0, os.SEEK_END)
        if not handle.tell():
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError('Dang co bo cai nhan ban khac chay. Dong cua so bo cai cua tool roi thu lai.') from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def selected_python(root):
    root = Path(root).resolve()
    _, pointer = _paths(root)
    try:
        record = json.loads(pointer.read_text(encoding='utf-8'))
        if not isinstance(record, dict):
            raise ValueError('invalid runtime record')
        name = record['environment']
        if (record.get('schema') != SCHEMA or not ENVIRONMENT.fullmatch(name)
                or record.get('fingerprint') != dependency_fingerprint(root)):
            raise ValueError('unverified or incompatible runtime')
        environment = root / name
        executable = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        if not environment.resolve().is_relative_to(root) or not executable.is_file():
            raise ValueError('missing runtime')
        return executable
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeError('Chua co bo may nhan ban cai xong. Chay install_clone_ai.bat, cho thanh cong roi mo start.bat.') from exc


def _stop_child(process):
    if process.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if os.name != 'nt':
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            process.kill()
        process.wait()


def _run(command, root, log=None):
    environment = dict(os.environ)
    environment['PYTHONUTF8'] = '1'
    environment['PIP_DISABLE_PIP_VERSION_CHECK'] = '1'
    environment['PATH'] = str(Path(root) / '.data' / 'tools' / 'ffmpeg' / 'bin') + os.pathsep + environment.get('PATH', '')
    options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
    process = subprocess.Popen([str(part) for part in command], cwd=root, env=environment,
                               stdout=subprocess.PIPE if log else None,
                               stderr=subprocess.STDOUT if log else None,
                               text=True, encoding='utf-8', errors='replace', **options)
    try:
        if log:
            for line in process.stdout:
                print(line, end='', flush=True)
                log.write(line)
                log.flush()
        code = process.wait()
    except BaseException:
        _stop_child(process)
        raise
    if code:
        raise subprocess.CalledProcessError(code, command)
    return code


def _validate(executable, root, log):
    _run([executable, '-m', 'pip', 'check'], root, log)
    _run([executable, '-c', 'import torch,torchaudio,onnxruntime,whisper,transformers,soundfile,fastapi,uvicorn; from hyperpyyaml import load_hyperpyyaml; print("Thu vien nhan ban da kiem tra xong.")'], root, log)
    _run([executable, '-c', 'import cosy_engine,sys; s=cosy_engine.availability(); print(s["reason"] or "Mo hinh cuc bo da san sang."); sys.exit(0 if s["ready"] else 1)'], root, log)


def install(root=BASE):
    import struct
    if sys.implementation.name != 'cpython' or not supported(sys.version_info, struct.calcsize('P') * 8):
        raise RuntimeError('Can CPython 3.10-3.12 64-bit; khuyen dung Python 3.12.')
    root = Path(root).resolve()
    with installer_lock(root):
        expected_fingerprint = dependency_fingerprint(root)
        folder, pointer = _paths(root)
        logfile = folder / ('install-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6] + '.log')
        with logfile.open('w', encoding='utf-8') as log:
            try:
                existing = None
                try:
                    existing = selected_python(root)
                except RuntimeError:
                    pass
                if existing:
                    print('Kiem tra bo may da cai. Khong cai de thu vien dang dung.', flush=True)
                    try:
                        _validate(existing, root, log)
                        if dependency_fingerprint(root) != expected_fingerprint:
                            raise RuntimeError('Tep cai dat da thay doi trong luc cai. Hay chay lai bo cai.')
                        return existing
                    except (subprocess.CalledProcessError, OSError):
                        print('Bo may cu chua dat kiem tra; se tao moi truong rieng moi, khong sua bo cu.', flush=True)
                name = '.venv-clone-' + uuid.uuid4().hex[:12]
                target = root / name
                if target.exists():
                    raise RuntimeError('Ten moi truong moi da ton tai; chay lai bo cai.')
                print('Dang tao moi truong NHAN BAN RIENG: ' + name, flush=True)
                print('Giu nguyen .venv cu, du lieu va cac mau giong.', flush=True)
                venv.EnvBuilder(with_pip=True).create(target)
                executable = target / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
                print('[1/5] Kiem tra FFmpeg...', flush=True)
                _run([executable, '-X', 'utf8', 'prepare_media_tools.py'], root, log)
                print('[2/5] Cai PyTorch CPU trong moi truong rieng...', flush=True)
                _run([executable, '-m', 'pip', 'install', '--no-input', '--only-binary=:all:', *TORCH,
                      '--index-url', 'https://download.pytorch.org/whl/cpu'], root, log)
                print('[3/5] Cai thu vien nhan ban...', flush=True)
                _run([executable, '-m', 'pip', 'install', '--no-input', '--only-binary=:all:',
                      '--no-binary=antlr4-python3-runtime,openai-whisper', '-r', 'requirements-cosy.txt'], root, log)
                print('[4/5] Tai/xac minh mo hinh; cac tep da dung duoc tai su dung...', flush=True)
                _run([executable, '-X', 'utf8', 'prepare_clone_model.py'], root, log)
                print('[5/5] Kiem tra truoc khi kich hoat...', flush=True)
                _validate(executable, root, log)
                if dependency_fingerprint(root) != expected_fingerprint:
                    raise RuntimeError('Tep cai dat da thay doi trong luc cai. Chua kich hoat; hay chay lai bo cai.')
                _atomic_json(pointer, {'schema': SCHEMA, 'environment': name,
                    'fingerprint': expected_fingerprint, 'created_at': datetime.now(timezone.utc).isoformat()})
                print('Da cai xong va kich hoat bo may nhan ban. Chay start.bat.', flush=True)
                return executable
            except BaseException:
                print('Chua cai xong; bo may cu va cac mau giong khong bi thay doi.', file=sys.stderr)
                print('Nhat ky: ' + str(logfile), file=sys.stderr)
                print('Neu thay WinError 32, dong Studio/cac bo cai cua tool; khoi dong lai Windows neu van bi giu tep.', file=sys.stderr)
                raise


def serve(root=BASE, *, open_browser=False):
    root = Path(root).resolve()
    executable = selected_python(root)
    print('Hmong Studio dang dung bo may nhan ban: ' + executable.parent.parent.name, flush=True)
    print('Mo trinh duyet: http://127.0.0.1:8090', flush=True)
    try:
        if open_browser:
            return _run([executable, '-X', 'utf8', 'open_studio.py'], root)
        return _run([executable, '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', '8090', '--no-access-log'], root)
    except KeyboardInterrupt:
        return 0
    except subprocess.CalledProcessError:
        print('Khong mo duoc Studio. Dong cua so Studio cu dang dung cong8090 roi chay lai CHAY-STUDIO.bat.', file=sys.stderr)
        raise


def launch(root=BASE):
    install(root)
    return serve(root, open_browser=True)


if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['install']:
            install()
        elif sys.argv[1:] == ['serve']:
            sys.exit(serve())
        elif sys.argv[1:] == ['launch']:
            sys.exit(launch())
        else:
            raise RuntimeError('Lenh ho tro: install, serve hoac launch.')
    except (Exception, KeyboardInterrupt) as exc:
        print('Khong hoan tat: ' + (str(exc) or 'Da dung theo yeu cau.'), file=sys.stderr)
        sys.exit(1)
