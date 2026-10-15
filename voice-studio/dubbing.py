"""Local video inspection and fast narration muxing; video frames are copied."""
import json
import math
import subprocess
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
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-protocol_whitelist', 'file,pipe', '-format_whitelist', 'mov,matroska,webm', '-i', str(source), '-i', str(audio), '-filter_complex', filters, '-map', '0:v:0', '-map', '[out]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-t', str(meta['duration']), '-movflags', '+faststart', '-y', str(temporary)], check=True, timeout=21600)
    destination = data / 'audio' / (job['id'] + '.mp4')
    temporary.replace(destination)
