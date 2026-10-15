"""Local video inspection and fast narration muxing; video frames are copied."""
import json
import math
import subprocess
import threading
from pathlib import Path


def inspect_video(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-protocol_whitelist', 'file,pipe', '-format_whitelist', 'mov,matroska,webm', '-show_streams', '-show_format', '-of', 'json', str(path)], capture_output=True, text=True, timeout=30, check=True)
    info = json.loads(result.stdout)
    video = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
    duration = float(info['format'].get('duration', 0))
    if not video or not math.isfinite(duration) or not 0 < duration <= 10800:
        raise ValueError('Video phải có hình ảnh và dài tối đa 3 giờ.')
    if video['codec_name'] not in {'h264', 'hevc', 'av1', 'mpeg4', 'vp9'}:
        raise ValueError('Codec chưa hỗ trợ xuất MP4 nhanh. Hãy chuyển video sang H.264 trước.')
    return {'duration': duration, 'codec': video['codec_name'], 'has_audio': any(s['codec_type'] == 'audio' for s in info['streams'])}


def run_ffmpeg(command, work, duration, start, end, phase, timeout=21600):
    """Use FFmpeg's processed timestamp, never a simulated percentage."""
    progress = work / 'progress.json'
    def update(value):
        try:
            current = json.loads(progress.read_text(encoding='utf-8')) if progress.exists() else {}
            current.update(progress=value, phase=phase)
            temporary = work / 'ffmpeg-progress.tmp'
            temporary.write_text(json.dumps(current, ensure_ascii=False), encoding='utf-8')
            # Readers may briefly hold progress.json on Windows.
            import time
            for attempt in range(10):
                try:
                    temporary.replace(progress)
                    break
                except PermissionError:
                    if attempt == 9:
                        raise
                    time.sleep(.05)
        except FileNotFoundError:
            pass
    update(start)
    with subprocess.Popen(command[:-1]+['-progress', 'pipe:1', '-nostats', command[-1]], stdout=subprocess.PIPE, text=True, encoding='utf-8', errors='replace') as process:
        timer = threading.Timer(timeout, process.kill)
        timer.daemon = True
        timer.start()
        try:
            for line in process.stdout:
                if line.startswith('out_time_us='):
                    try:
                        seconds = int(line.strip().split('=', 1)[1])/1000000
                        update(min(end, start+int((end-start)*seconds/max(duration, .001))))
                    except ValueError:
                        pass
            if process.wait():
                raise subprocess.CalledProcessError(process.returncode, command)
        finally:
            timer.cancel()
            if process.poll() is None:
                process.kill()
                process.wait()
    update(end)


def mux_video(job, audio, work, data, audio_seconds):
    meta = json.loads((data / 'videos' / (job['video_id'] + '.json')).read_text(encoding='utf-8'))
    offset = job.get('video_offset', 0)
    if audio_seconds + offset > meta['duration'] + .05:
        raise ValueError(f'Lời đọc dài {audio_seconds:.1f}s, vượt khoảng còn lại của video ({meta["duration"]-offset:.1f}s). Rút ngắn lời hoặc tăng tốc độ đọc; ứng dụng không tự cắt mất lời.')
    source = data / 'videos' / (job['video_id'] + '.source')
    temporary = work / 'dubbed.mp4'
    delay = round(offset * 1000)
    filters = f'[1:a]adelay={delay}:all=1,apad[dub]'
    if job.get('video_mix') and meta['has_audio']:
        filters += ';[0:a:0]volume=0.15[background];[dub][background]amix=inputs=2:duration=first:normalize=0[out]'
    else:
        filters += ';[dub]anull[out]'
    run_ffmpeg(['ffmpeg', '-nostdin', '-v', 'error', '-protocol_whitelist', 'file,pipe', '-format_whitelist', 'mov,matroska,webm', '-i', str(source), '-i', str(audio), '-filter_complex', filters, '-map', '0:v:0', '-map', '[out]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-t', str(meta['duration']), '-movflags', '+faststart', '-y', str(temporary)], work, meta['duration'], 86, 99, 'Đang xuất video MP4')
    destination = data / 'audio' / (job['id'] + '.mp4')
    temporary.replace(destination)
