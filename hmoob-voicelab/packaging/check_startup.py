"""Exercise normal BAT cold startup, browser intent and actual HTTP readiness."""
from __future__ import annotations

import argparse
import http.client
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == '--browser-probe':
        Path(sys.argv[2]).write_text(sys.argv[3], encoding='utf-8')
        return 0
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('--reports', required=True, type=Path)
    parser.add_argument('--model-dir', type=Path)
    parser.add_argument('--timeout', type=int, default=1800)
    args = parser.parse_args()
    root, reports = args.root.resolve(), args.reports.resolve()
    reports.mkdir(parents=True, exist_ok=True)
    data = reports / 'cold-start-data'
    marker = reports / 'browser-opened.txt'
    if marker.exists():
        raise ValueError('Cold-start reports must not contain a previous browser marker')
    environment = dict(os.environ)
    environment['PYTHONUTF8'] = '1'
    environment['PYTHONUNBUFFERED'] = '1'
    environment['HMOOB_DATA_DIR'] = str(data)
    environment['BROWSER'] = ('"' + (root / 'runtime' / 'python.exe').as_posix() + '" "' +
                              Path(__file__).resolve().as_posix() + '" --browser-probe "' +
                              marker.as_posix() + '" %s')
    for name in ('PYTHONHOME', 'PYTHONPATH', 'HMOOB_MODEL_DIR', 'MPLCONFIGDIR', 'NUMBA_CACHE_DIR', 'XDG_CACHE_HOME'):
        environment.pop(name, None)
    if args.model_dir:
        environment['HMOOB_MODEL_DIR'] = str(args.model_dir.resolve())
    comspec = environment.get('COMSPEC', r'C:\Windows\System32\cmd.exe')
    command = subprocess.list2cmdline([comspec, '/d', '/s', '/c']) + ' ""' + str(root / 'MO_HMOOB_VOICELAB.bat') + '" --port 0"'
    process = subprocess.Popen(command, cwd=root, env=environment, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding='utf-8', errors='replace')
    messages = queue.Queue()
    captured = []

    def collect():
        for line in process.stdout:
            captured.append(line)
            messages.put(line)
        messages.put(None)
    threading.Thread(target=collect, daemon=True).start()
    started = time.monotonic()
    first_output = None
    port = None
    try:
        deadline = started + args.timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError('Normal BAT stopped before opening the app: ' + ''.join(captured)[-5000:])
            try:
                line = messages.get(timeout=.5)
            except queue.Empty:
                if first_output is None and time.monotonic() - started >= 10:
                    raise TimeoutError('The launcher produced no immediate startup message')
                continue
            if line is None:
                raise RuntimeError('Normal BAT closed its output before readiness')
            if first_output is None:
                first_output = time.monotonic() - started
                assert first_output < 10, 'The launcher remained silent for too long'
            match = re.search(r'http://127\.0\.0\.1:(\d+)', line)
            if match:
                port = int(match.group(1))
                break
        if port is None:
            raise TimeoutError('Normal startup did not become ready; see captured log')
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=30)
        try:
            connection.request('GET', '/api/status')
            response = connection.getresponse()
            status = json.loads(response.read())
            assert response.status == 200 and status['engine']['ready'] and status['ffmpeg'], status
            connection.request('GET', '/')
            response = connection.getresponse()
            assert response.status == 200 and b'Hmoob' in response.read()
            connection.request('GET', '/api/voices')
            response = connection.getresponse()
            voices = json.loads(response.read())['voices']
            assert response.status == 200 and len(voices) == 2 and all(voice['reference_ready'] for voice in voices)
        finally:
            connection.close()
        deadline = time.monotonic() + 30
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(.25)
        assert marker.exists(), 'Normal startup did not invoke a browser'
        assert marker.read_text(encoding='utf-8') == 'http://127.0.0.1:' + str(port)
        log = data / '.logs' / 'launch.log'
        assert log.is_file() and 'http://127.0.0.1:' in log.read_text(encoding='utf-8')
        result = {'normal_bat_started': True, 'first_output_seconds': first_output,
                  'ready_seconds': time.monotonic() - started, 'http_ready': True,
                  'both_reference_defaults_ready': True, 'browser_invoked': True,
                  'durable_log_present': True, 'models_verified': True}
        (reports / 'cold-startup.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result), flush=True)
    finally:
        if process.poll() is None:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            process.wait(timeout=30)
        (reports / 'cold-startup-console.log').write_text(''.join(captured), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
