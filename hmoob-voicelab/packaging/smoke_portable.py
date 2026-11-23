"""Exercise a relocated native runtime, real voices and persisted HTTP outputs."""
from __future__ import annotations

from array import array
import http.client
import io
import json
import math
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
import wave
import zipfile


def request(port, method, path, payload=None):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=30)
    body = None if payload is None else json.dumps(payload).encode('utf-8')
    headers = {} if body is None else {'Content-Type': 'application/json'}
    try:
        connection.request(method, path, body, headers)
        response = connection.getresponse()
        result = response.read()
        if response.status != 200 and not (method == 'POST' and response.status == 201):
            raise RuntimeError(str(response.status) + ': ' + result.decode('utf-8', errors='replace'))
        return result
    finally:
        connection.close()


def wav_info(raw):
    with wave.open(io.BytesIO(raw), 'rb') as recording:
        assert recording.getnchannels() == 1 and recording.getsampwidth() == 2
        rate, frames = recording.getframerate(), recording.getnframes()
        assert rate == 24000 and 0 < frames <= rate * 120
        pcm = recording.readframes(frames)
        assert len(pcm) == frames * 2
    samples = array('h', pcm)
    if sys.byteorder != 'little':
        samples.byteswap()
    rms = math.sqrt(sum(value * value for value in samples) / len(samples)) / 32768
    assert rms > 1e-6
    return {'frames': frames, 'rate': rate, 'seconds': frames / rate, 'rms': rms}


def start_app(root, reports):
    app, runtime = root / 'hmoob-voicelab', root / 'runtime' / 'python.exe'
    # Run the real application in-process after installing a Python socket
    # guard. Only loopback HTTP connections are permitted during synthesis;
    # unused plotting/ASR entry points must never load in the real renderer.
    program = r'''
import runpy, socket, sys
from pathlib import Path
unused = ('f5_tts.api', 'f5_tts.infer.utils_infer', 'matplotlib', 'transformers')
def guard_unused(event, arguments):
    blocked = ''
    if event == 'import' and arguments:
        name = str(arguments[0])
        if any(name == module or name.startswith(module + '.') for module in unused):
            blocked = name
    elif event == 'exec' and arguments:
        filename = str(getattr(arguments[0], 'co_filename', '')).replace('\\', '/').lower()
        for module in unused:
            fragment = module.replace('.', '/')
            module_file = ('/' + fragment + '.py' if '.' in module else
                           '/site-packages/' + fragment + '.py')
            if '/' + fragment + '/' in filename or filename.endswith(module_file):
                blocked = module
                break
    if blocked:
        print('HMOOB_UNUSED_IMPORT_BLOCKED:' + blocked, flush=True)
        raise RuntimeError('Real synthesis attempted an unused plotting/ASR module: ' + blocked)
sys.addaudithook(guard_unused)
print('HMOOB_UNUSED_IMPORT_GUARD:active', flush=True)
app = Path(sys.argv[1])
data = sys.argv[2]
original = socket.socket.connect
def local_connect(self, address):
    if not isinstance(address, tuple) or address[0] not in ('127.0.0.1', 'localhost', '::1'):
        raise RuntimeError('Portable smoke blocked external network access')
    return original(self, address)
socket.socket.connect = local_connect
sys.path.insert(0, str(app))
sys.argv = [str(app / 'launch.py'), '--no-browser', '--port', '0', '--data-dir', data]
runpy.run_path(str(app / 'launch.py'), run_name='__main__')
'''
    process = subprocess.Popen([str(runtime), '-u', '-c', program, str(app), str(reports / 'smoke-data')],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               encoding='utf-8', errors='replace', cwd=app, env=os.environ.copy())
    lines = queue.Queue()
    log = []

    def collect():
        for line in process.stdout:
            log.append(line)
            lines.put(line)
    threading.Thread(target=collect, daemon=True).start()
    deadline = time.monotonic() + 120
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError('Portable application stopped: ' + ''.join(log)[-4000:])
            try:
                line = lines.get(timeout=.25)
            except queue.Empty:
                continue
            match = re.search(r'http://127\.0\.0\.1:(\d+)', line)
            if match:
                return process, int(match.group(1)), log
        raise RuntimeError('Portable application did not start')
    except Exception:
        process.terminate()
        process.wait(30)
        raise


def stop_app(process):
    process.terminate()
    try:
        process.wait(30)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(30)


def main():
    root, reports = (Path(argument).resolve() for argument in sys.argv[1:3])
    app, runtime = root / 'hmoob-voicelab', root / 'runtime'
    assert Path(sys.prefix).resolve() == runtime
    assert ' ' in str(root), 'Relocation smoke must use a directory with spaces'
    import torch
    assert Path(torch.__file__).resolve().is_relative_to(runtime)
    check = subprocess.run([str(runtime / 'python.exe'), str(app / 'bootstrap.py'), '--check'],
                           capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
    if check.returncode:
        raise RuntimeError('Relocated bootstrap failed: ' + check.stdout + check.stderr)
    assert json.loads(check.stdout.strip().splitlines()[-1])['ready']
    launcher = root / 'MO_HMOOB_VOICELAB.bat'
    comspec = os.environ.get('COMSPEC', r'C:\Windows\System32\cmd.exe')
    # CMD /s /c needs an outer quote pair around a quoted batch path and its
    # arguments. Pass this exact native command line without an extra shell.
    command = subprocess.list2cmdline([comspec, '/d', '/s', '/c']) + ' ""' + str(launcher) + '" --check"'
    launched = subprocess.run(command, shell=False, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, encoding='utf-8',
                              errors='replace', timeout=180, cwd=root)
    launch_status = None
    for line in reversed(launched.stdout.splitlines()):
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict) and 'ready' in value:
            launch_status = value
            break
    if launched.returncode or not launch_status or not launch_status['ready']:
        raise RuntimeError('One-click BAT failed after relocation: ' + launched.stdout + launched.stderr)
    text = 'Nyob zoo. Kuv yog Hmoob.'
    results = []
    process, port, log = start_app(root, reports)
    try:
        status = json.loads(request(port, 'GET', '/api/status'))
        assert status['engine']['ready'] and status['ffmpeg']
        voices = json.loads(request(port, 'GET', '/api/voices'))['voices']
        assert len(voices) == 2 and all(voice['reference_ready'] for voice in voices)
        assert b'Hmoob' in request(port, 'GET', '/')
        for voice in ('female', 'male'):
            job = json.loads(request(port, 'POST', '/api/jobs',
                                     {'voice': voice, 'text': text, 'quality': 'fast', 'speed': 1.0}))['job']
            deadline = time.monotonic() + 600
            while job['status'] not in ('done', 'error', 'cancelled') and time.monotonic() < deadline:
                time.sleep(.5)
                job = json.loads(request(port, 'GET', '/api/jobs/' + job['id']))['job']
            assert job['status'] == 'done', job
            assert job['progress'] == 100 and job['completed_segments'] == job['total_segments']
            raw = request(port, 'GET', job['parts'][0]['url'])
            audio = wav_info(raw)
            downloaded = request(port, 'GET', '/api/jobs/' + job['id'] + '/archive')
            with zipfile.ZipFile(io.BytesIO(downloaded)) as archive:
                assert archive.read('script.txt').decode('utf-8') == text
                manifest = json.loads(archive.read('manifest.json'))
                assert manifest['status'] == 'done'
                assert wav_info(archive.read(job['parts'][0]['name'])) == audio
            results.append({'voice': voice, 'job_id': job['id'], 'audio': audio,
                            'synthesis_seconds': job['synthesis_seconds']})
        assert any('HMOOB_UNUSED_IMPORT_GUARD:active' in line for line in log)
        assert not any('HMOOB_UNUSED_IMPORT_BLOCKED:' in line for line in log), ''.join(log)
    finally:
        stop_app(process)
        (reports / 'native-app.log').write_text(''.join(log), encoding='utf-8')
    process, port, log = start_app(root, reports)
    try:
        history = json.loads(request(port, 'GET', '/api/jobs'))['jobs']
        assert all(any(job['id'] == result['job_id'] and job['status'] == 'done' for job in history)
                   for result in results)
    finally:
        stop_app(process)
    report = {'relocated_runtime': str(runtime), 'text': text, 'voices': results,
              'external_network_blocked': True, 'bootstrap_ready': True,
              'one_click_bat_ready': True,
              'unused_inference_modules_blocked': ['f5_tts.api', 'f5_tts.infer.utils_infer',
                                                   'matplotlib', 'transformers'],
              'unused_inference_modules_attempted': False,
              'http_audio_and_zip_verified': True, 'history_survives_restart': True,
              'speech_quality_assessed': False}
    (reports / 'native-smoke.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
