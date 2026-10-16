"""Local video inspection and fast narration muxing; video frames are copied."""
import json
import math
import os
import subprocess
import time
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
    rotation = next((abs(int(s.get('rotation', 0))) % 180 for s in video.get('side_data_list', []) if 'rotation' in s), 0)
    width, height = video['width'], video['height']
    if rotation == 90:
        width, height = height, width
    return {'width': width, 'height': height, 'duration': duration, 'codec': video['codec_name'], 'has_audio': any(s['codec_type'] == 'audio' for s in info['streams'])}


def run_ffmpeg(command, work, duration, start, end, phase, timeout=21600, cwd=None):
    """Poll real FFmpeg timestamps without blocking on Windows pipe EOF."""
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


def mux_video(job, audio, work, data, audio_seconds):
    meta = json.loads((data / 'videos' / (job['video_id'] + '.json')).read_text(encoding='utf-8'))
    offset = job.get('video_offset', 0)
    if audio_seconds + offset > meta['duration'] + .001:
        raise ValueError(f'Lời đọc dài {audio_seconds:.1f}s, vượt khoảng còn lại của video ({meta["duration"]-offset:.1f}s). Rút ngắn lời hoặc tăng tốc độ đọc; ứng dụng không tự cắt mất lời.')
    source = data / 'videos' / (job['video_id'] + '.source')
    temporary = work / 'dubbed.mp4'
    delay = round(offset * 1000)
    filters = f'[1:a]adelay={delay}:all=1,apad=whole_dur={meta["duration"]}[dub]'
    if job.get('video_mix') and meta['has_audio']:
        filters += ';[0:a:0]volume=0.15[background];[dub][background]amix=inputs=2:duration=first:normalize=0[out]'
    else:
        filters += ';[dub]anull[out]'
    from video_tasks import logo_filters
    from video_export import scale_filter,encoder_options
    meta.update(inspect_video(source))
    logo = logo_filters(job, meta)
    scale,size = scale_filter(meta,job.get('export_resolution','original'))
    video_filters = [f for f in (logo,scale) if f]
    if job.get('caption_cues'):
        from video_editor import validate_cues,write_ass
        cues=validate_cues(job['caption_cues'],meta['duration'])
        write_ass(work/'captions.ass',cues,*size)
        video_filters.append('ass=filename=captions.ass')
    video_options = ['-vf', ','.join(video_filters), *encoder_options(job)] if video_filters else ['-c:v', 'copy']
    run_ffmpeg(['ffmpeg', '-nostdin', '-v', 'error', '-protocol_whitelist', 'file,pipe', '-format_whitelist', 'mov,matroska,webm', '-i', str(source), '-i', str(audio), '-filter_complex', filters, '-map', '0:v:0', '-map', '[out]', *video_options, '-c:a', 'aac', '-b:a', '192k', '-t', str(meta['duration']), '-movflags', '+faststart', '-y', str(temporary)], work, meta['duration'], 86, 99, 'Đang xuất video MP4', timeout=max(600,meta['duration']*8) if video_filters else max(60,meta['duration']*2),cwd=work)
    destination = data / 'audio' / (job['id'] + '.mp4')
    temporary.replace(destination)
