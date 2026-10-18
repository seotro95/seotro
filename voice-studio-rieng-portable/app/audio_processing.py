"""FFmpeg audio export with observable, cancellable-worker progress."""
import os
import subprocess
import time
from state_io import read_progress, write_progress

def run_ffmpeg(command, work, duration, start, end, phase, timeout=21600, cwd=None):
    """Poll real FFmpeg timestamps without blocking on Windows pipe EOF."""
    progress = work / 'progress.json'
    def update(value):
        current=read_progress(progress)
        current.update(progress=value,phase=phase)
        write_progress(progress,current)
    update(start)
    status_file = work / 'ffmpeg-status.txt'
    status_file.unlink(missing_ok=True)
    # Windows can keep a progress pipe open after FFmpeg finishes. A sidecar
    # file avoids waiting for pipe EOF and still reports real output timestamps.
    args = command[:-1]+['-progress', str(status_file), '-nostats', command[-1]]
    if os.environ.get('CI') == 'true' and '-v' in args:
        args[args.index('-v')+1] = 'info'
    error_log = work / 'ffmpeg-errors.log'
    with error_log.open('ab') as errors, subprocess.Popen(args, cwd=cwd, stdout=subprocess.DEVNULL, stderr=errors) as process:
        started = time.monotonic()
        last = start
        def read_status():
            nonlocal last
            try:
                with status_file.open('rb') as source:
                    source.seek(0, 2)
                    source.seek(max(0, source.tell()-8192))
                    lines = source.read().decode('utf-8', errors='replace').splitlines()
                for line in reversed(lines):
                    if line.startswith('out_time_us='):
                        seconds = int(line.split('=', 1)[1])/1000000
                        value = max(last, min(end, start+int((end-start)*seconds/max(duration,.001))))
                        if value != last:
                            update(value)
                            last = value
                        break
            except (OSError, ValueError):
                pass
        try:
            while process.poll() is None:
                read_status()
                if time.monotonic()-started > timeout:
                    raise subprocess.TimeoutExpired(args, timeout)
                time.sleep(.15)
            read_status()
            if process.returncode:
                raise subprocess.CalledProcessError(process.returncode, command)
        except subprocess.SubprocessError as exc:
            diagnostic = error_log.read_bytes()[-5000:].decode('utf-8', errors='replace')
            try:
                diagnostic += '\nProgress: '+status_file.read_bytes()[-1200:].decode('utf-8', errors='replace')
            except OSError:
                pass
            exc.add_note(diagnostic)
            raise
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
    update(end)


