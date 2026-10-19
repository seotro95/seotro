"""Local video preparation. No platform posting or cloud credentials required."""
import json
import math
import shutil
import subprocess
import threading
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parent
DATA = ROOT / '.data'
DATA.mkdir(exist_ok=True)
app = FastAPI(title='Video Affiliate Studio')
LOCK = threading.Lock()


def save(folder, state):
    temporary = folder / 'job.tmp'
    temporary.write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
    temporary.replace(folder / 'job.json')


def command(args, cwd):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=3600)
    if result.returncode:
        raise ValueError(result.stderr[-2500:] or 'FFmpeg không thành công')
    return result.stdout


def render(folder, state):
    with LOCK:
        try:
            state['status'] = 'Đang dựng'
            save(folder, state)
            probe = json.loads(command(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', 'source'], folder))
            duration = float(probe['format']['duration'])
            if not any(s['codec_type'] == 'video' for s in probe['streams']):
                raise ValueError('Tệp nguồn không có video.')
            if state['start'] >= duration:
                raise ValueError('Mốc bắt đầu vượt thời lượng video.')
            length = min(state['duration'], duration - state['start'])
            vf = 'scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1'
            if state['title']:
                (folder / 'title.txt').write_text(state['title'], encoding='utf-8')
                vf += ',drawtext=textfile=title.txt:expansion=none:fontcolor=white:fontsize=36:box=1:boxcolor=black@0.6:boxborderw=12:x=(w-tw)/2:y=80'
            if (folder / 'subtitles.srt').exists():
                vf += ",subtitles=subtitles.srt:force_style='FontSize=18,Outline=2,MarginV=60'"
            args = ['ffmpeg', '-y', '-v', 'error', '-ss', str(state['start']), '-i', 'source']
            if (folder / 'music').exists():
                args += ['-stream_loop', '-1', '-i', 'music']
            if (folder / 'logo').exists():
                logo_index = 2 if (folder / 'music').exists() else 1
                args += ['-i', 'logo', '-filter_complex', f'[0:v]{vf}[base];[{logo_index}:v]scale=110:-1[logo];[base][logo]overlay=W-w-24:24[v]', '-map', '[v]']
            else:
                args += ['-vf', vf, '-map', '0:v:0']
            args += ['-map', '1:a:0' if (folder / 'music').exists() else '0:a:0?', '-t', str(length), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-threads', '2', '-c:a', 'aac', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', 'video.mp4']
            command(args, folder)
            caption = f"{state['title']}\n\n{state['description']}\n\n{state['product']}\n{state['link']}\n\n{state['hashtags']}"
            if state['link']:
                caption += '\nTiếp thị liên kết: tôi có thể nhận hoa hồng khi bạn mua qua liên kết.'
            (folder / 'caption.txt').write_text(caption.strip(), encoding='utf-8-sig')
            (folder / 'posting-plan.json').write_text(json.dumps({'planned_at': state['planned_at'], 'status': 'Chờ bạn duyệt và đăng thủ công', 'product': state['product'], 'affiliate_url': state['link']}, ensure_ascii=False, indent=2), encoding='utf-8')
            with zipfile.ZipFile(folder / 'bundle.zip', 'w', zipfile.ZIP_STORED) as archive:
                for name in ['video.mp4', 'caption.txt', 'posting-plan.json']:
                    archive.write(folder / name, name)
            state['status'] = 'Hoàn tất'
        except Exception as exc:
            state['status'] = 'Lỗi'
            state['error'] = str(exc)
        save(folder, state)


@app.get('/')
def home():
    return FileResponse(ROOT / 'index.html')


@app.get('/api/jobs')
def jobs():
    rows = []
    for path in DATA.glob('*/job.json'):
        try:
            rows.append(json.loads(path.read_text(encoding='utf-8')))
        except (OSError, ValueError):
            continue
    return sorted(rows, key=lambda x: x['created'], reverse=True)


async def store(upload, path, limit):
    size = 0
    with path.open('wb') as output:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                raise HTTPException(413, 'Tệp vượt giới hạn dung lượng.')
            output.write(chunk)


@app.post('/api/jobs', status_code=202)
async def create(video: UploadFile = File(...), music: UploadFile | None = File(None), logo: UploadFile | None = File(None), subtitles: UploadFile | None = File(None), title: str = Form(''), description: str = Form(''), product: str = Form(''), link: str = Form(''), hashtags: str = Form('#video #review'), start: float = Form(0), duration: float = Form(30), planned_at: str = Form('')):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise HTTPException(503, 'Cần cài FFmpeg và ffprobe vào PATH, sau đó khởi động lại tool.')
    if not math.isfinite(start) or not math.isfinite(duration) or start < 0 or not 1 <= duration <= 180:
        raise HTTPException(400, 'Bắt đầu phải >= 0; độ dài từ 1 đến 180 giây.')
    if len(title) > 80 or any(len(x) > 5000 for x in [description, product, hashtags, link]):
        raise HTTPException(400, 'Tiêu đề tối đa 80 ký tự, các ô khác tối đa 5000 ký tự.')
    if link and (urlparse(link).scheme not in ('http', 'https') or not urlparse(link).hostname):
        raise HTTPException(400, 'Liên kết cần bắt đầu bằng http:// hoặc https://.')
    folder = DATA / uuid.uuid4().hex
    folder.mkdir()
    try:
        await store(video, folder / 'source', 500 * 1024 * 1024)
        for upload, name, limit in [(music, 'music', 50 * 1024 * 1024), (logo, 'logo', 10 * 1024 * 1024), (subtitles, 'subtitles.srt', 2 * 1024 * 1024)]:
            if upload and upload.filename:
                await store(upload, folder / name, limit)
        state = dict(id=folder.name, title=title, description=description, product=product, link=link, hashtags=hashtags, start=start, duration=duration, planned_at=planned_at, created=datetime.now(timezone.utc).isoformat(), status='Đang chờ')
        save(folder, state)
    except Exception:
        shutil.rmtree(folder)
        raise
    threading.Thread(target=render, args=(folder, state), daemon=True).start()
    return {'id': folder.name}


@app.get('/files/{job_id}/{name}')
def download(job_id: str, name: str):
    if len(job_id) != 32 or any(c not in '0123456789abcdef' for c in job_id) or name not in ['video.mp4', 'caption.txt', 'bundle.zip', 'posting-plan.json']:
        raise HTTPException(404)
    folder = DATA / job_id
    try:
        ready = json.loads((folder / 'job.json').read_text(encoding='utf-8'))['status'] == 'Hoàn tất'
    except (OSError, ValueError):
        ready = False
    if not ready or not (folder / name).is_file():
        raise HTTPException(404)
    return FileResponse(folder / name, filename=name)


if __name__ == '__main__':
    # Jobs cannot resume safely after an interrupted encoder.
    for path in DATA.glob('*/job.json'):
        state = json.loads(path.read_text(encoding='utf-8'))
        if state['status'] in ('Đang chờ', 'Đang dựng'):
            state.update(status='Lỗi', error='Ứng dụng đã tắt giữa chừng. Vui lòng tạo lại tác vụ.')
            save(path.parent, state)
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8787)
