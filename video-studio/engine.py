"""Persistent media library, cancellable jobs, FFmpeg and local CPU engines."""
from __future__ import annotations
import concurrent.futures
import contextlib
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from subtitles import parse_srt, to_srt

ROOT = Path(__file__).resolve().parent
RESOURCE_ROOT = Path(getattr(sys, '_MEIPASS', ROOT))
DATA = Path(os.environ.get('VIDEO_STUDIO_DATA', str(ROOT / 'data'))).expanduser().resolve()
DATA.mkdir(parents=True, exist_ok=True)
DB = DATA / 'studio.sqlite3'
LOCK = threading.RLock()
POOL = concurrent.futures.ThreadPoolExecutor(max_workers=2)
EVENTS = {}
PROCESSES = {}



@contextlib.contextmanager
def db():
    with LOCK:
        connection = sqlite3.connect(DB)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()


with db() as c:
    c.executescript('''CREATE TABLE IF NOT EXISTS assets
      (id TEXT PRIMARY KEY, name TEXT, path TEXT, kind TEXT, metadata TEXT, created REAL);
      CREATE TABLE IF NOT EXISTS jobs
      (id TEXT PRIMARY KEY, action TEXT, name TEXT, status TEXT, progress INTEGER,
       result TEXT, error TEXT, created REAL);''')
    c.execute("UPDATE jobs SET status='interrupted', error='Ứng dụng đã khởi động lại. Hãy tạo lượt xử lý mới.' WHERE status IN ('queued','running','cancelling')")


def executable(name):
    suffix = '.exe' if os.name == 'nt' else ''
    for root in (RESOURCE_ROOT, ROOT, ROOT / 'bin'):
        candidate = root / (name + suffix)
        if candidate.is_file():
            return str(candidate)
    result = shutil.which(name)
    if not result:
        raise ValueError(f'Chưa có {name}. Đặt FFmpeg cạnh launcher hoặc thêm vào PATH.')
    return result


def list_assets():
    with db() as c:
        return [public_asset(r) for r in c.execute('SELECT * FROM assets ORDER BY created DESC')]


def public_asset(row):
    return {'id': row['id'], 'name': row['name'], 'kind': row['kind'],
            'metadata': json.loads(row['metadata']), 'created': row['created']}


def asset(identifier):
    with db() as c:
        row = c.execute('SELECT * FROM assets WHERE id=?', (identifier,)).fetchone()
    if row is None:
        raise ValueError('Không tìm thấy tệp trong thư viện.')
    path = Path(row['path'])
    if not path.resolve().is_relative_to(DATA) or not path.is_file():
        raise ValueError('Tệp đã bị di chuyển hoặc xóa.')
    return dict(row)


def probe(path):
    result = subprocess.run([executable('ffprobe'), '-v', 'error', '-show_entries',
                             'stream=codec_type,width,height:format=duration', '-of', 'json', str(path)],
                            capture_output=True, timeout=40)
    if result.returncode:
        raise ValueError('FFprobe không đọc được tệp media này.')
    data = json.loads(result.stdout)
    streams = data.get('streams', [])
    duration = float(data.get('format', {}).get('duration') or 0)
    if not streams or duration <= 0:
        raise ValueError('Media không có luồng âm thanh/video hoặc thời lượng hợp lệ.')
    video = next((s for s in streams if s['codec_type'] == 'video'), {})
    return {'duration': round(duration, 3), 'width': video.get('width'), 'height': video.get('height'),
            'has_audio': any(s['codec_type'] == 'audio' for s in streams)}


def register(path, name=None):
    path = Path(path).resolve()
    assert path.is_relative_to(DATA)
    if path.suffix.lower() == '.srt':
        cues = parse_srt(path.read_text(encoding='utf-8-sig'))
        metadata = {'cues': len(cues), 'duration': cues[-1]['end']}
        kind = 'subtitle'
    elif path.suffix.lower() == '.txt':
        try:
            path.read_text(encoding='utf-8-sig')
        except UnicodeDecodeError:
            raise ValueError('Tệp TXT cần được lưu ở định dạng UTF-8.') from None
        metadata, kind = {}, 'text'
    else:
        metadata = probe(path)
        kind = 'video' if metadata.get('width') else 'audio'
    identifier = str(uuid.uuid4())
    with db() as c:
        c.execute('INSERT INTO assets VALUES (?,?,?,?,?,?)',
                  (identifier, name or path.name, str(path), kind, json.dumps(metadata), time.time()))
    return identifier


class Cancelled(Exception):
    pass


def check_cancel(job):
    if EVENTS[job].is_set():
        raise Cancelled()


def stop_process(process):
    if process.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)
    else:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
    with contextlib.suppress(subprocess.TimeoutExpired):
        process.wait(timeout=5)


def command(job, args, cwd=None, timeout=3600):
    check_cancel(job)
    log = DATA / 'jobs' / job / 'process.log'
    with log.open('wb') as output:
        kwargs = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
        process = subprocess.Popen(args, stdout=output, stderr=subprocess.STDOUT, cwd=cwd, **kwargs)
        with LOCK:
            PROCESSES[job] = process
        deadline = time.monotonic() + timeout
        try:
            while process.poll() is None:
                check_cancel(job)
                if time.monotonic() > deadline:
                    raise ValueError('Tác vụ vượt giới hạn thời gian. Hãy dùng video ngắn hơn.')
                progress_file = log.parent / 'progress.json'
                if progress_file.exists():
                    with contextlib.suppress(OSError, ValueError, KeyError):
                        update(job, progress=min(95, max(5, int(json.loads(progress_file.read_text())['progress']))))
                time.sleep(.1)
            check_cancel(job)
            if process.returncode:
                # Network tools can include signed URLs or cookie data in errors.
                if args[0] == executable('ffmpeg'):
                    message = log.read_text(errors='replace')[-800:]
                elif (log.parent / 'error.json').exists():
                    message = json.loads((log.parent / 'error.json').read_text())['message']
                else:
                    message = 'Nguồn tải từ chối hoặc không phản hồi; kiểm tra link, cookie và kết nối.'
                raise ValueError('Xử lý thất bại: ' + message)
        finally:
            stop_process(process)
            with LOCK:
                PROCESSES.pop(job, None)


def update(job, **fields):
    if 'result' in fields:
        fields['result'] = json.dumps(fields['result'])
    with db() as c:
        c.execute('UPDATE jobs SET ' + ','.join(f'{key}=?' for key in fields) + ' WHERE id=?',
                  (*fields.values(), job))


def jobs():
    with db() as c:
        result = [dict(r) for r in c.execute('SELECT * FROM jobs ORDER BY created DESC LIMIT 200')]
    for item in result:
        item['result'] = json.loads(item['result']) if item['result'] else None
    return result


def enqueue(action, name, payload):
    job = str(uuid.uuid4())
    (DATA / 'jobs' / job).mkdir(parents=True)
    with db() as c:
        c.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?)',
                  (job, action, name, 'queued', 0, None, None, time.time()))
    EVENTS[job] = threading.Event()
    POOL.submit(run_job, job, action, payload)
    return job


def cancel(job):
    with LOCK:
        event = EVENTS.get(job)
        if not event:
            raise ValueError('Tác vụ không còn chạy.')
        # The lock also serializes cancellation with final publication of results.
        with db() as c:
            row = c.execute('SELECT status FROM jobs WHERE id=?', (job,)).fetchone()
        if not row or row['status'] not in ('queued', 'running', 'cancelling'):
            raise ValueError('Tác vụ đã kết thúc.')
        event.set()
        update(job, status='cancelling')


def run_job(job, action, payload):
    folder = DATA / 'jobs' / job
    registered = []
    try:
        check_cancel(job)
        update(job, status='running', progress=5)
        output = perform(job, action, payload, folder)
        with LOCK:
            check_cancel(job)
            for path, name in output:
                registered.append(register(path, name))
            update(job, status='done', progress=100, result={'asset_ids': registered})
    except Cancelled:
        update(job, status='cancelled', error='Đã dừng tác vụ; tệp nguồn được giữ nguyên.')
    except Exception as exc:
        # Known errors have sanitized messages; unexpected provider data is not exposed.
        message = str(exc) if isinstance(exc, ValueError) else 'Xử lý thất bại. Kiểm tra dữ liệu đầu vào và cấu hình.'
        update(job, status='error', error=message[:1200])
    finally:
        with LOCK:
            EVENTS.pop(job, None)


def run_local(job, action, payload, folder):
    configuration = folder / 'payload.json'
    configuration.write_text(json.dumps({**payload, 'action':action}, ensure_ascii=False), encoding='utf-8')
    worker = [sys.executable, '--offline-worker'] if getattr(sys, 'frozen', False) else [sys.executable, str(RESOURCE_ROOT / 'offline_worker.py')]
    command(job, [*worker, str(configuration)], timeout=7200)
    name = {'tts':'giong_doc.wav', 'stt':'phu_de.srt', 'translate':'phu_de_dich.srt', 'prepare':'model_san_sang.txt'}[action]
    return [(folder / name, name)]


def perform(job, action, p, folder):
    ffmpeg = executable('ffmpeg')
    if action == 'download':
        worker = [sys.executable, '--download-worker'] if getattr(sys, 'frozen', False) else [sys.executable, str(RESOURCE_ROOT / 'download_worker.py')]
        command(job, [*worker, p['url'], str(folder)], timeout=1800)
        files = [f for f in folder.iterdir() if f.suffix.lower() in ('.mp4', '.mkv', '.webm', '.mov')]
        if not files:
            raise ValueError('Nguồn không trả về video hoàn chỉnh.')
        return [(f, f.name) for f in files]
    if action == 'ai':
        from text_tools import edit_text
        out = folder / 'bien_tap.txt'
        out.write_text(edit_text(p['prompt'], p['task']), encoding='utf-8')
        return [(out, out.name)]
    if action in ('tts', 'prepare'):
        return run_local(job, action, p, folder)
    source = asset(p['asset_id'])
    path = Path(source['path'])
    meta = json.loads(source['metadata'])
    if action == 'stt':
        if source['kind'] not in ('video', 'audio') or not meta.get('has_audio'):
            raise ValueError('Tệp cần có âm thanh để tạo phụ đề.')
        return run_local(job, action, {**p, 'source':str(path)}, folder)
    if action == 'translate':
        if source['kind'] != 'subtitle':
            raise ValueError('Hãy chọn tệp SRT để dịch.')
        return run_local(job, action, {**p, 'source':str(path)}, folder)
    if action == 'render':
        if source['kind'] != 'video':
            raise ValueError('Render cần tệp video.')
        start, end = p['start'], p['end'] or meta['duration']
        if start >= meta['duration'] or end <= start or end > meta['duration'] + .1:
            raise ValueError('Khoảng cắt phải nằm trong thời lượng video.')
        args = [ffmpeg, '-nostdin', '-y', '-v', 'error', '-ss', str(start), '-t', str(end - start), '-i', str(path)]
        audio_meta = None
        if p.get('audio_id'):
            audio = asset(p['audio_id'])
            audio_meta = json.loads(audio['metadata'])
            if not audio_meta.get('has_audio'):
                raise ValueError('Tệp lồng tiếng không có âm thanh.')
            args += ['-i', audio['path']]
        filters = []
        if p['height']:
            filters.append(f"scale=-2:{p['height']}")
        else:
            filters.append('scale=trunc(iw/2)*2:trunc(ih/2)*2')
        filters.append(f"setpts=PTS/{p['speed']}")
        if p.get('subtitle_id'):
            subtitle = asset(p['subtitle_id'])
            if subtitle['kind'] != 'subtitle':
                raise ValueError('Phụ đề cần là tệp SRT.')
            cues = parse_srt(Path(subtitle['path']).read_text(encoding='utf-8-sig'))
            # Shift timestamps to the trimmed/speed-adjusted output timeline.
            shifted = [{'start': max(0, c['start'] - start) / p['speed'],
                        'end': (min(c['end'], end) - start) / p['speed'], 'text': c['text']}
                       for c in cues if c['end'] > start and c['start'] < end]
            if not shifted:
                raise ValueError('Không có phụ đề trong khoảng cắt đã chọn.')
            (folder / 'subtitle.srt').write_text(to_srt(shifted), encoding='utf-8')
            color = p['subtitle_color'].lstrip('#')
            bgr = color[4:6] + color[2:4] + color[0:2]
            font_family = 'Arial' if os.name == 'nt' else 'DejaVu Sans'
            filters.append(f"subtitles=subtitle.srt:force_style='FontName={font_family},FontSize={p['font_size']},PrimaryColour=&H00{bgr},Outline=2,MarginV=25'")
        if p['title']:
            (folder / 'title.txt').write_text(p['title'], encoding='utf-8')
            title_font = ''
            if os.name == 'nt':
                system_font = Path(os.environ.get('WINDIR', 'C:\\Windows')) / 'Fonts' / 'arial.ttf'
                if system_font.is_file():
                    shutil.copyfile(system_font, folder / 'titlefont.ttf')
                    title_font = ':fontfile=titlefont.ttf'
            filters.append("drawtext=textfile=title.txt:expansion=none" + title_font + ":fontcolor=white:fontsize=30:box=1:boxcolor=black@0.5:boxborderw=12:x=(w-tw)/2:y=30")
        args += ['-vf', ','.join(filters), '-map', '0:v:0']
        if audio_meta:
            args += ['-map', '1:a:0', '-af', 'apad', '-t', str((end - start) / p['speed'])]
        elif meta.get('has_audio'):
            args += ['-map', '0:a:0', '-af', f"atempo={p['speed']}"]
        args += ['-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', '-crf', str(p['crf']), '-c:a', 'aac', '-movflags', '+faststart', str(folder / 'video_xuat.mp4')]
        command(job, args, cwd=folder)
        return [(folder / 'video_xuat.mp4', Path(source['name']).stem + '_xuat.mp4')]
    raise ValueError('Tác vụ không được hỗ trợ.')
