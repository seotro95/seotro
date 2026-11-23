"""Prepare missing local prerequisites once, then open Hmoob VoiceLab.

The portable distribution already contains Python, dependencies and FFmpeg.
An installed Python can also prepare an isolated .venv for the source edition.
No environment, model, reference recording or user job is deleted by this file.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time

BASE = Path(__file__).resolve().parent
PROBE_PREFIX = 'HMOOB_PROBE:'


class SetupError(RuntimeError):
    pass


def progress(message):
    # stderr keeps --check stdout machine-readable while remaining visible in
    # the console and the portable launcher's combined diagnostic log.
    print(message, file=sys.stderr, flush=True)


def python_candidates(base=BASE):
    """Prefer the supplied portable runtime, then a saved local environment."""
    base = Path(base)
    for root in (base, base.parent):
        for folder in ('runtime', 'python'):
            yield root / folder / 'python.exe', 'portable'
    yield base / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python'), 'venv'


def select_python(base=BASE):
    for candidate, kind in python_candidates(base):
        if candidate.is_file():
            return str(candidate), kind
    return sys.executable, 'system'


def _json_probe(python, code, environment, timeout=60, label='Python'):
    try:
        result = subprocess.run([str(python), '-c', code], env=environment,
                                capture_output=True, text=True, encoding='utf-8', errors='replace',
                                timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise SetupError(f'Kiểm tra {label} quá {timeout} giây. Bước đang dừng đã hiện trong '
                         'cửa sổ khởi động; xem nhật ký để xác định thư viện chưa nạp được.') from exc
    for line in reversed(result.stdout.splitlines()):
        if line.startswith(PROBE_PREFIX):
            return json.loads(line[len(PROBE_PREFIX):])
    detail = (result.stderr or result.stdout).strip()[-500:]
    raise SetupError('Không kiểm tra được Python đã chọn. ' + detail)


def check_python(python, environment):
    result = _json_probe(python, "import json,struct,sys; print('HMOOB_PROBE:' + json.dumps("
                         "{'major':sys.version_info.major,'minor':sys.version_info.minor,"
                         "'bits':struct.calcsize('P')*8}))", environment)
    if result['major'] != 3 or result['minor'] not in (10, 11, 12) or result['bits'] != 64:
        raise SetupError('Bộ tạo giọng cần Python 3.10–3.12 64-bit. Dùng bản Portable đầy đủ '
                         'hoặc cài Python 3.12 64-bit. Môi trường và dữ liệu cũ được giữ nguyên.')


def configure_environment(base, data, inherited=None):
    environment = dict(os.environ if inherited is None else inherited)
    # Isolate this tool's interpreter without altering the user's saved/global
    # environment. Keep networking, proxy and TLS trust variables inherited.
    environment.pop('PYTHONHOME', None)
    environment.pop('PYTHONPATH', None)
    environment['PYTHONNOUSERSITE'] = '1'
    environment['PYTHONUTF8'] = '1'
    environment['PYTHONUNBUFFERED'] = '1'
    environment['HMOOB_DATA_DIR'] = str(Path(data).resolve())
    environment.setdefault('HMOOB_MODEL_DIR', str(Path(data).resolve() / 'models'))
    environment['HF_HUB_OFFLINE'] = '1'
    environment['TRANSFORMERS_OFFLINE'] = '1'
    for name, folder in (('MPLCONFIGDIR', 'matplotlib'), ('NUMBA_CACHE_DIR', 'numba'),
                         ('XDG_CACHE_HOME', 'xdg')):
        environment.setdefault(name, str(Path(data).resolve() / 'cache' / folder))
    suffix = '.exe' if os.name == 'nt' else ''
    for root in (Path(base), Path(base).parent):
        for folder in ('ffmpeg/bin', 'ffmpeg', 'bin'):
            candidate = root / folder
            if all((candidate / (name + suffix)).is_file() for name in ('ffmpeg', 'ffprobe')):
                environment['PATH'] = str(candidate) + os.pathsep + environment.get('PATH', '')
                return environment
    return environment


def check_ffmpeg(environment):
    missing = [name for name in ('ffmpeg', 'ffprobe')
               if not shutil.which(name, path=environment.get('PATH'))]
    if missing:
        raise SetupError('Thiếu ' + ', '.join(missing) + '. Bản Portable đầy đủ có sẵn hai tệp này. '
                         'Với bản mã nguồn, cài FFmpeg và ffprobe vào PATH, hoặc đặt cả hai '
                         'trong thư mục ffmpeg/bin cạnh tool. Không cần cài lại hay xóa dữ liệu.')


DEPENDENCY_INVENTORY = """
import importlib.metadata
import importlib.util
import json
result = {'ready': False, 'torch_pair_ready': False, 'versions': {}, 'error': '',
          'native_checked': False, 'validation': 'installed-packages'}
try:
    for name in ('torch', 'torchaudio', 'f5-tts'):
        result['versions'][name] = importlib.metadata.version(name)
    torch_version = result['versions']['torch'].split('+')[0]
    audio_version = result['versions']['torchaudio'].split('+')[0]
    result['torch_pair_ready'] = (torch_version == audio_version and
        torch_version.split('.')[:2] in (['2','6'], ['2','7'], ['2','8']))
    result['missing_modules'] = [name for name in ('torch','torchaudio','numpy','soundfile','f5_tts','vocos','safetensors')
                                 if importlib.util.find_spec(name) is None]
    result['ready'] = (result['torch_pair_ready'] and result['versions']['f5-tts'] == '1.1.22'
                       and not result['missing_modules'])
    if result['missing_modules']:
        result['error'] = 'Thiếu gói: ' + ', '.join(result['missing_modules'])
except Exception as exc:
    result['error'] = type(exc).__name__ + ': ' + str(exc)[:300]
"""


def _streamed_json_probe(python, code, environment, *, stage_timeout=120, total_timeout=600):
    """Stream diagnostic import stages while bounding each and the whole probe."""
    process = subprocess.Popen([str(python), '-u', '-c', code], env=environment,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding='utf-8', errors='replace', bufsize=1)
    lines = queue.Queue()

    def read_output():
        try:
            for line in process.stdout:
                lines.put(line.rstrip('\r\n'))
        except (OSError, ValueError):
            pass
        finally:
            lines.put(None)

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    started = time.monotonic()
    deadline = started + stage_timeout
    stage = 'khởi động tiến trình kiểm tra'
    stage_started = started
    report, recent = None, []
    try:
        while True:
            remaining = min(deadline, started + total_timeout) - time.monotonic()
            if remaining <= 0:
                limit = (f'tổng thời gian {total_timeout} giây' if time.monotonic() >= started + total_timeout
                         else f'{stage_timeout} giây cho bước này')
                raise SetupError(f'Kiểm tra AI dừng ở {stage}, vượt {limit}. '
                                 'Nhật ký có tên thư viện và dấu vết đang nạp; giao diện thường '
                                 'không cần chạy phép kiểm tra chuyên sâu này khi mở tool.')
            try:
                line = lines.get(timeout=min(.25, remaining))
            except queue.Empty:
                continue
            if line is None:
                break
            if line.startswith('HMOOB_NATIVE_START:'):
                stage = line.split(':', 1)[1]
                stage_started = time.monotonic()
                deadline = stage_started + stage_timeout
                progress('Kiểm tra chuyên sâu: đang nạp ' + stage + '…')
            elif line.startswith('HMOOB_NATIVE_DONE:'):
                progress(f'Đã nạp {stage} trong {time.monotonic() - stage_started:.1f} giây.')
            elif line.startswith(PROBE_PREFIX):
                report = json.loads(line[len(PROBE_PREFIX):])
            elif line:
                recent = (recent + [line])[-12:]
                progress(line)
        process.wait(timeout=5)
        if report is None:
            raise SetupError('Kiểm tra AI chưa trả kết quả ở ' + stage + '. ' + '\n'.join(recent)[-2000:])
        return report
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        reader.join(timeout=1)
        process.stdout.close()


def dependency_state(python, environment, *, deep=False):
    # The already-built portable runtime must not block its HTTP interface on
    # unused plotting/ASR/training imports. Installed packages are sufficient
    # for startup; actual model loading belongs to the synthesis worker. CI
    # separately proves speech generation. Native diagnostics remain explicit.
    if not deep:
        return _json_probe(python, DEPENDENCY_INVENTORY + "\n"
                           "print('HMOOB_PROBE:' + json.dumps(result))", environment,
                           timeout=45, label='các gói thư viện đã cài')
    code = DEPENDENCY_INVENTORY + """
if result['ready']:
    import faulthandler
    import importlib
    import time
    faulthandler.dump_traceback_later(45, repeat=True)
    try:
        result['ready'] = False
        result['validation'] = 'native-imports'
        result['native_import_seconds'] = {}
        for name in ('torch', 'torchaudio', 'numpy', 'soundfile', 'f5_tts.model', 'vocos', 'safetensors.torch'):
            result['native_stage'] = name
            started = time.monotonic()
            print('HMOOB_NATIVE_START:' + name, flush=True)
            module = importlib.import_module(name)
            if name == 'f5_tts.model':
                getattr(module, 'CFM')
                getattr(module, 'DiT')
            elif name == 'vocos':
                getattr(module, 'Vocos')
            elif name == 'safetensors.torch':
                getattr(module, 'load_file')
            result['native_import_seconds'][name] = round(time.monotonic() - started, 3)
            print('HMOOB_NATIVE_DONE:' + name, flush=True)
        result['native_stage'] = None
        result['native_checked'] = True
        result['ready'] = True
    except Exception as exc:
        result['error'] = type(exc).__name__ + ': ' + str(exc)[:500]
    finally:
        faulthandler.cancel_dump_traceback_later()
print('HMOOB_PROBE:' + json.dumps(result))
"""
    return _streamed_json_probe(python, code, environment)


def models_ready(python, base, environment):
    try:
        result = subprocess.run([str(python), str(Path(base) / 'setup_voice.py'), '--verify-only'],
                                env=environment, cwd=base, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=180)
    except subprocess.TimeoutExpired as exc:
        raise SetupError('Kiểm tra SHA-256 mô hình quá 180 giây. Mô hình và dữ liệu vẫn được giữ '
                         'nguyên; xem nhật ký khởi động để kiểm tra tốc độ đọc tệp.') from exc
    return result.returncode == 0


def run_step(command, environment, base, message):
    print(message, flush=True)
    result = subprocess.run([str(value) for value in command], env=environment, cwd=base)
    if result.returncode:
        raise SetupError(message + ' chưa hoàn tất. Xem lỗi phía trên và chạy lại start. '
                         'Các tệp dữ liệu, đoạn âm thanh và mô hình đã lưu vẫn được giữ nguyên.')


def prepare_runtime(python, kind, base, environment, state):
    base = Path(base)
    if kind == 'system':
        folder = base / '.venv'
        if folder.exists():
            raise SetupError('Thư mục .venv đã có nhưng thiếu Python dùng được. Tool không xóa '
                             'hoặc ghi đè môi trường cũ. Dùng bản Portable đầy đủ hoặc đổi tên '
                             'riêng thư mục .venv trước khi chạy lại; giữ nguyên .data.')
        run_step([python, '-m', 'venv', folder], environment, base,
                 'Chuẩn bị môi trường riêng .venv…')
        python = str(folder / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python'))
        kind = 'venv'
        check_python(python, environment)
        state = {'ready': False, 'torch_pair_ready': False}
    if not state['ready']:
        pip = subprocess.run([python, '-m', 'pip', '--version'], env=environment,
                             cwd=base, capture_output=True, text=True,
                             encoding='utf-8', errors='replace', timeout=45)
        if pip.returncode:
            run_step([python, '-m', 'ensurepip', '--upgrade'], environment, base,
                     'Chuẩn bị pip trong môi trường tạo giọng…')
        if not state.get('torch_pair_ready'):
            command = [python, '-m', 'pip', 'install', 'torch==2.6.0', 'torchaudio==2.6.0']
            if sys.platform != 'darwin':
                command += ['--index-url', 'https://download.pytorch.org/whl/cpu']
            run_step(command, environment, base,
                     'Cài PyTorch/torchaudio CPU 2.6.0; lần đầu cần Internet…')
        run_step([python, '-m', 'pip', 'install', '-r', base / 'requirements-voice.txt'],
                 environment, base, 'Cài thư viện F5-Hmong…')
        state = dependency_state(python, environment)
        if not state['ready']:
            raise SetupError('Thư viện đã cài nhưng chưa chạy được: ' + state.get('error', '') +
                             '. Dữ liệu cũ vẫn được giữ nguyên. Dùng bản Portable phù hợp Windows 64-bit.')
    if not models_ready(python, base, environment):
        # setup_voice uses explicit HTTPS URLs and checksum verification. It
        # does not rely on Hugging Face's automatic cache downloader.
        run_step([python, base / 'setup_voice.py'], environment, base,
                 'Tải và xác minh F5-Hmong/Vocos, khoảng 1,4 GB; chỉ cần chuẩn bị một lần…')
        if not models_ready(python, base, environment):
            raise SetupError('Mô hình chưa vượt kiểm tra SHA-256. Kiểm tra mạng/dung lượng rồi '
                             'chạy lại; không bỏ kiểm tra checksum.')
    return python


def main(argv=None, *, base=BASE):
    parser = argparse.ArgumentParser(description='Mở Hmoob VoiceLab; tự chuẩn bị phần còn thiếu ở lần đầu.')
    parser.add_argument('--setup', action='store_true', help='Chuẩn bị phần còn thiếu rồi thoát')
    parser.add_argument('--check', action='store_true', help='Chỉ kiểm tra, không cài hoặc tải mô hình')
    parser.add_argument('--deep-check', '--diagnose', action='store_true',
                        help='Chẩn đoán nạp thư viện AI theo từng bước, không cài hoặc tải mô hình')
    parser.add_argument('--data-dir', type=Path, default=None)
    args, launch_arguments = parser.parse_known_args(argv)
    if args.setup and (args.check or args.deep_check):
        parser.error('Không dùng --setup cùng --check hoặc --deep-check.')
    base = Path(base).resolve()
    data = args.data_dir or Path(os.getenv('HMOOB_DATA_DIR', str(base / '.data')))
    environment = configure_environment(base, data)
    try:
        progress('Hmoob VoiceLab — đang khởi động. Giữ cửa sổ này mở.')
        python, kind = select_python(base)
        progress('[1/4] Kiểm tra Python đi kèm…')
        check_python(python, environment)
        progress('[2/4] Kiểm tra FFmpeg và FFprobe…')
        check_ffmpeg(environment)
        progress('[3/4] Chẩn đoán nạp thư viện AI theo từng gói…' if args.deep_check else
                 '[3/4] Kiểm tra các gói thư viện đã cài; không nạp AI khi mở giao diện…')
        state = (dependency_state(python, environment, deep=True) if args.deep_check
                 else dependency_state(python, environment))
        if not state['ready'] and state.get('error'):
            progress('Thư viện AI chưa sẵn sàng: ' + state['error'])
        progress('[4/4] Kiểm tra mô hình và SHA-256; chưa có mô hình sẽ tải ở bước kế tiếp…')
        verified = models_ready(python, base, environment)
        if args.check or args.deep_check:
            print(json.dumps({'ready': bool(state['ready'] and verified),
                              'dependencies': state, 'models_verified': verified,
                              'python': str(python)}, ensure_ascii=False), flush=True)
            return 0 if state['ready'] and verified else 1
        if not state['ready'] or not verified:
            print('Lần đầu tool tự chuẩn bị phần còn thiếu. Giữ cửa sổ này mở; '
                  'những lần sau dùng lại thư viện và mô hình trên máy.', flush=True)
            data.resolve().mkdir(parents=True, exist_ok=True)
            python = prepare_runtime(python, kind, base, environment, state)
        if args.setup:
            print('Đã sẵn sàng. Mở start.bat (Windows) hoặc bash start.sh để dùng tool.', flush=True)
            return 0
        command = [str(python), str(base / 'launch.py'), '--data-dir', str(data.resolve()),
                   *launch_arguments]
        progress('Đã sẵn sàng. Đang mở giao diện trên trình duyệt…')
        return subprocess.run(command, cwd=base, env=environment).returncode
    except KeyboardInterrupt:
        print('\nĐã dừng. Tiến độ đã lưu sẽ được dùng lại khi mở tool.', flush=True)
        return 0
    except (SetupError, OSError, subprocess.SubprocessError, ValueError) as exc:
        print('Chưa mở được Hmoob VoiceLab: ' + str(exc), file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
