"""Show startup progress and retain it without importing native AI libraries."""
from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

BASE = Path(__file__).resolve().parent
HEARTBEAT_SECONDS = 15


def data_directory(arguments, base=BASE):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--data-dir', type=Path)
    settings, _ = parser.parse_known_args(arguments)
    return (settings.data_dir or Path(os.getenv('HMOOB_DATA_DIR', str(Path(base) / '.data')))).resolve()


def main(arguments=None, *, base=BASE):
    arguments = list(sys.argv[1:] if arguments is None else arguments)
    diagnose = '--diagnose' in arguments
    arguments = [argument for argument in arguments if argument != '--diagnose']
    if diagnose and '--check' not in arguments:
        arguments.append('--check')
    if diagnose and '--deep-check' not in arguments:
        arguments.append('--deep-check')
    base = Path(base).resolve()
    print('Hmoob VoiceLab: Python da khoi dong. Dang kiem tra tool...', flush=True)
    try:
        data = data_directory(arguments, base)
        folder = data / '.logs'
        folder.mkdir(parents=True, exist_ok=True)
        log_path = folder / ('diagnostic.log' if diagnose else 'launch.log')
        with log_path.open('a', encoding='utf-8', buffering=1) as log:
            def record(message, *, display=True):
                message = str(message).rstrip('\r\n')
                log.write(datetime.now().isoformat(timespec='seconds') + ' ' + message + '\n')
                log.flush()
                if display:
                    print(message, flush=True)

            record('Log: ' + str(log_path))
            record('Python: ' + sys.version.split()[0] + ' | ' + sys.executable)
            normalized_arguments = list(arguments)
            for index, value in enumerate(normalized_arguments):
                if value == '--data-dir' and index + 1 < len(normalized_arguments):
                    normalized_arguments[index + 1] = str(data)
                elif value.startswith('--data-dir='):
                    normalized_arguments[index] = '--data-dir=' + str(data)
            environment = dict(os.environ, HMOOB_DATA_DIR=str(data))
            command = [sys.executable, '-u', str(base / 'bootstrap.py'), *normalized_arguments]
            try:
                process = subprocess.Popen(command, cwd=base, stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT, text=True,
                                           encoding='utf-8', errors='replace', bufsize=1,
                                           env=environment)
            except OSError as exc:
                record('Khong chay duoc bootstrap: ' + str(exc))
                return 1
            messages = queue.Queue()

            def collect():
                try:
                    for line in process.stdout:
                        messages.put(line)
                finally:
                    process.stdout.close()
                    messages.put(None)
            threading.Thread(target=collect, daemon=True).start()
            started = last_message = time.monotonic()
            application_ready = False
            try:
                while True:
                    try:
                        message = messages.get(timeout=1)
                    except queue.Empty:
                        if not application_ready and time.monotonic() - last_message >= HEARTBEAT_SECONDS:
                            record('Van dang chuan bi (' + str(int(time.monotonic() - started)) +
                                   ' giay). Lan dau co the mat vai phut; xem log o tren.')
                            last_message = time.monotonic()
                        continue
                    if message is None:
                        break
                    record(message)
                    last_message = time.monotonic()
                    application_ready = application_ready or 'http://127.0.0.1:' in message
                code = process.wait()
            except KeyboardInterrupt:
                record('Dang dung tool; cac doan da luu van duoc giu lai.')
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                return 130
            if code:
                record('Tool dung voi ma loi ' + str(code) + '. Gui tep log o tren de kiem tra.')
            else:
                record('Kiem tra hoan tat.' if diagnose or '--check' in arguments else 'Tool da dung.')
            return code
    except (OSError, ValueError) as exc:
        print('Khong tao duoc log/khoi dong tool: ' + str(exc), file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
