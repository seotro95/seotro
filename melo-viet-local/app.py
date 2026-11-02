"""Persistent local jobs, bounded chunk processing and optional international online voices."""
import argparse
import atexit
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
import wave
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

from documents import MAX_CHARS, STYLES, parse_document, plan_document, Assembler, convert_audio

VERSION = '1.1.0'
LABELS = {'VI':'Việt · VieNeu Turbo', 'EN':'Anh · MeloTTS', 'FR':'Pháp · MeloTTS', 'JP':'Nhật · MeloTTS',
          'KR':'Hàn · MeloTTS', 'ES':'Tây Ban Nha · MeloTTS', 'ZH':'Trung · MeloTTS'}
TERMINAL = {'done', 'error', 'cancelled', 'interrupted'}
IDENT = re.compile(r'^[a-f0-9]{32}$')
CACHE_REVISION = 'melo209145-vieneu3.8.3-edge7.3.1-pcm-v1'


def atomic_json(path, body):
    temporary = path.with_suffix('.json.partial')
    temporary.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def wave_seconds(path):
    with wave.open(str(path), 'rb') as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getnframes() <= 0:
            raise ValueError('WAV không hợp lệ.')
        return audio.getnframes() / audio.getframerate()


class Reader:
    def __init__(self,root,engine,offline=False):
        self.root,self.engine,self.offline=Path(root),engine,offline
        self.lock=threading.Lock();self.process=None;self.log=None

    def close(self):
        process,self.process=self.process,None
        if process is not None and process.poll() is None:
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
        if self.log:self.log.close();self.log=None

    def request(self,payload,cancel=None):
        with self.lock:
            if cancel is not None and cancel.is_set():raise InterruptedError('Đã dừng.')
            if self.process is None or self.process.poll() is not None:
                self.close()
                python=self.root/'envs'/self.engine/'bin/python'
                if not python.is_file():raise ValueError('Chưa cài môi trường. Chạy CAI_DAT.bat trước.')
                logs=self.root/'logs';logs.mkdir(exist_ok=True)
                self.log=(logs/(self.engine+'.log')).open('a',encoding='utf-8')
                env=dict(os.environ,MELO_VIET_ROOT=str(self.root),HF_HOME=str(self.root/'models/huggingface'),
                    HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',GRADIO_ANALYTICS_ENABLED='False',
                    OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='4',OMP_NUM_THREADS='4',PYTHONUNBUFFERED='1')
                if self.offline:env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
                self.process=subprocess.Popen([str(python),'-u',str(Path(__file__).with_name('worker.py'))],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,encoding='utf-8',env=env,start_new_session=True)
                process=self.process
                if cancel is not None and cancel.is_set():self.close();raise InterruptedError('Đã dừng.')
                ready=process.stdout.readline()
                if not ready or not json.loads(ready).get('ready'):raise RuntimeError('Không mở được bộ đọc. Chạy CAP_NHAT.bat nếu vừa nâng cấp; xem logs trong thư mục cài.')
            process=self.process
            try:
                process.stdin.write(json.dumps(payload,ensure_ascii=False)+'\n');process.stdin.flush()
                line=process.stdout.readline()
                if not line:raise RuntimeError('Bộ đọc đã dừng. Xem logs/melo.log hoặc logs/viet.log trong thư mục cài.')
                result=json.loads(line)
                if not result.get('ok'):raise RuntimeError(result.get('error','Không tạo được giọng.'))
                return result
            except (BrokenPipeError,json.JSONDecodeError):
                self.close();raise RuntimeError('Mất kết nối với bộ đọc. Thử tải lại ngôn ngữ.') from None


class Studio:
    def __init__(self, root, offline=False, reader_factory=Reader):
        self.root = Path(root); self.offline = offline; self.reader_factory = reader_factory
        for name in ('outputs', 'cache/audio', 'logs'):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock(); self.condition = threading.Condition(self.lock)
        self.jobs = {}; self.events = {}; self.readers = {}; self.job = None
        self.closed = False; self.parallelism = 2; self.free_slots = set(range(4))
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='voice-job')
        for file in (self.root / 'outputs').glob('*/job.json'):
            try:
                item = json.loads(file.read_text(encoding='utf-8'))
                if not IDENT.fullmatch(item['id']):
                    continue
                if item['status'] not in TERMINAL:
                    item.update(status='interrupted', error='Tool đã đóng giữa tác vụ. Bấm Tiếp tục để dùng lại đoạn đã tạo.')
                    atomic_json(file, item)
                self.jobs[item['id']] = item
            except (OSError, ValueError, KeyError):
                continue
        # Preserve access to WAVs created before the history feature existed.
        for file in (self.root / 'outputs').glob('*.json'):
            if IDENT.fullmatch(file.stem) and file.stem not in self.jobs:
                try:
                    item = json.loads(file.read_text(encoding='utf-8'))
                    if (file.with_suffix('.wav')).is_file():
                        self.jobs[file.stem] = {**item, 'id': file.stem, 'status':'done', 'op':'render',
                            'created_at': datetime.fromtimestamp(file.stat().st_mtime, timezone.utc).isoformat(),
                            'title':'Bản thu cũ', 'legacy':True, 'audio_url':'/audio/'+file.stem+'.wav'}
                except (OSError, ValueError):
                    pass
        atexit.register(self.close)

    def persist(self, job):
        if not job.get('legacy'):
            atomic_json(self.root / 'outputs' / job['id'] / 'job.json', job)

    def snapshot(self, job):
        return json.loads(json.dumps(job, ensure_ascii=False))

    def list_jobs(self, limit=50, offset=0):
        with self.lock:
            ordered = sorted(self.jobs.values(), key=lambda j:j['created_at'], reverse=True)
            return {'jobs':[{k:v for k,v in self.snapshot(j).items() if k not in {'voices','locales'}} for j in ordered[offset:offset+limit]], 'total':len(ordered),
                    'parallelism':self.parallelism, 'running':sum(j['status']=='running' for j in ordered)}

    def close(self):
        with self.condition:
            if self.closed:
                return
            self.closed = True
            for event in self.events.values():
                event.set()
            for job in self.jobs.values():
                if job['status'] in {'queued', 'running'}:
                    job.update(status='interrupted', error='Tool đã đóng giữa tác vụ. Có thể tiếp tục bằng các đoạn đã lưu.')
                    self.persist(job)
            self.condition.notify_all()
        for reader in list(self.readers.values()):
            reader.close()
        self.executor.shutdown(wait=False, cancel_futures=True)

    def settings(self, parallelism):
        if type(parallelism) is not int or not 1 <= parallelism <= 4:
            raise ValueError('Chọn 1–4 bản tạo đồng thời.')
        with self.condition:
            self.parallelism = parallelism; self.condition.notify_all()
        return {'parallelism':parallelism}

    def validate(self, body):
        if not isinstance(body, dict):
            raise ValueError('Tác vụ cần là một đối tượng JSON.')
        engine = body.get('engine', 'local'); op = body.get('op', 'render')
        if engine not in {'local', 'edge'} or op not in {'voices', 'render', 'catalog'}:
            raise ValueError('Kiểm tra bộ đọc và thao tác.')
        language = body.get('language', 'VI'); threads = body.get('threads', 4)
        if type(threads) is not int or not 1 <= threads <= 16:
            raise ValueError('Chọn 1–16 luồng CPU cho mỗi bản.')
        if engine == 'edge':
            if self.offline:
                raise ValueError('Chế độ ngoại tuyến không gọi giọng trực tuyến. Mở MO_TOOL.bat để dùng Internet.')
            if op != 'catalog' and (not isinstance(language, str) or not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z0-9]{2,8}){1,2}', language)):
                raise ValueError('Chọn ngôn ngữ/quốc gia từ danh mục trực tuyến.')
        elif language not in LABELS or op == 'catalog':
            raise ValueError('Ngôn ngữ chưa có trong bộ đọc ngoại tuyến; chọn Trực tuyến để xem các tiếng khác.')
        normalized = {'op':op, 'engine':engine, 'language':language, 'threads':threads}
        if op == 'render':
            document = parse_document(body.get('text'), body.get('name', ''), body.get('format', 'auto'))
            speed = body.get('speed', 1.0); style = body.get('style', 'neutral'); size = body.get('chunk_size', 480)
            if type(speed) not in {int, float} or not math.isfinite(speed) or not .5 <= speed <= 2:
                raise ValueError('Tốc độ đọc cần từ 0,5× đến 2×.')
            if style not in STYLES or type(size) is not int or not 80 <= size <= 1200:
                raise ValueError('Kiểm tra kiểu đọc và độ dài đoạn (80–1.200 ký tự).')
            voice = body.get('voice')
            if not isinstance(voice, str) or not voice or len(voice) > 160:
                raise ValueError('Chọn một giọng đọc thực trong danh sách.')
            normalized.update(text=body['text'], voice=voice, speed=speed, style=style, chunk_size=size,
                              format=document['format'], name=str(body.get('name') or 'Lời đọc')[:200],
                              use_cache=bool(body.get('use_cache', True)))
        return normalized

    def start_batch(self, bodies):
        if not isinstance(bodies, list) or not 1 <= len(bodies) <= 32:
            raise ValueError('Mỗi lần gửi tối đa 32 tác vụ; có thể gửi thêm sau.')
        normalized = [self.validate(body) for body in bodies]
        with self.condition:
            if self.closed:
                raise ValueError('Tool đang đóng.')
            active = [j for j in self.jobs.values() if j['status'] in {'queued', 'running'}]
            if len(active) + len(normalized) > 64:
                raise ValueError('Hàng đợi tối đa 64 tác vụ. Chờ bớt trước khi thêm.')
            if sum(j.get('characters',0) for j in active) + sum(len(b.get('text','')) for b in normalized) > 16_000_000:
                raise ValueError('Tổng văn bản đang chờ tối đa 16 triệu ký tự.')
            result = []
            for body in normalized:
                ident = uuid.uuid4().hex; folder = self.root / 'outputs' / ident; folder.mkdir()
                atomic_json(folder / 'input.json', body)
                job = {'id':ident, 'status':'queued', 'op':body['op'], 'engine':body['engine'], 'language':body['language'],
                    'voice':body.get('voice',''), 'title':body.get('name','Chuẩn bị giọng'),
                    'created_at':datetime.now(timezone.utc).isoformat(), 'characters':len(body.get('text','')),
                    'completed_chunks':0, 'total_chunks':0, 'cache_hits':0, 'progress':0,
                    'speed':body.get('speed',1), 'style':body.get('style','neutral')}
                self.jobs[ident] = job; self.job = job; self.events[ident] = threading.Event(); self.persist(job)
                self.executor.submit(self.work, ident, body)
                result.append(self.snapshot(job))
            return result

    def start(self, body):
        return self.start_batch([body])[0]

    def reader_for(self, slot, body):
        engine = 'online' if body['engine'] == 'edge' else ('viet' if body['language']=='VI' else 'melo')
        key = (slot, engine)
        if key not in self.readers:
            self.readers[key] = self.reader_factory(self.root, engine, self.offline)
        return self.readers[key]

    def update(self, ident, **fields):
        with self.lock:
            job = self.jobs[ident]
            if job['status'] in {'cancelled', 'interrupted'}:
                raise InterruptedError('Đã dừng.')
            job.update(fields); self.persist(job)

    def work(self, ident, body):
        event = self.events[ident]; slot = None; assembler = None
        folder = self.root / 'outputs' / ident
        try:
            with self.condition:
                while not self.closed and not event.is_set():
                    running = 4 - len(self.free_slots)
                    waiting = next((j['id'] for j in self.jobs.values() if j['status']=='queued'),None)
                    if ident == waiting and running < self.parallelism and self.free_slots:
                        slot = min(self.free_slots); self.free_slots.remove(slot); break
                    self.condition.wait()
                if slot is None or event.is_set():
                    raise InterruptedError('Đã dừng.')
                self.update(ident, status='running', started_at=datetime.now(timezone.utc).isoformat())
                self.condition.notify_all()
            started = time.perf_counter(); reader = self.reader_for(slot, body); reader.owner = ident
            if body['op'] != 'render':
                result = reader.request(body, event)
                self.update(ident, **{k:v for k,v in result.items() if k!='ok'}, status='done', progress=1)
                return
            document = parse_document(body['text'], body['name'], body['format'])
            chunks = plan_document(document, body['chunk_size'])
            self.update(ident, total_chunks=len(chunks), warnings=document['warnings'])
            (folder / 'script.txt').write_text(document['text'], encoding='utf-8')
            if document['format'] == 'srt':
                (folder / 'original.srt').write_text(body['text'], encoding='utf-8')
            assembler = Assembler(folder); total_load = 0; cache_hits = 0; raw_seconds = 0; spoken_chars = 0
            for index, text in enumerate(chunks):
                if event.is_set():
                    raise InterruptedError('Đã dừng.')
                fingerprint = json.dumps([CACHE_REVISION, body['engine'], body['language'], body['voice'], text], ensure_ascii=False)
                digest = hashlib.sha256(fingerprint.encode()).hexdigest(); cache = self.root / 'cache/audio' / (digest+'.wav')
                hit = False
                if body['use_cache'] and cache.is_file():
                    try:
                        raw_seconds += wave_seconds(cache); hit = True
                    except (OSError, EOFError, wave.Error, ValueError):
                        pass
                if not hit:
                    raw = folder / 'raw.wav'
                    result = reader.request({**body, 'text':text, 'output':str(raw)}, event)
                    total_load += result.get('model_load_seconds',0)
                    raw_seconds += wave_seconds(raw)
                    if event.is_set():
                        raise InterruptedError('Đã dừng.')
                    # Unique temp file prevents simultaneous jobs from sharing a partial WAV.
                    temporary = cache.with_name(digest+'.'+ident+'.partial.wav')
                    shutil.copyfile(raw, temporary); temporary.replace(cache)
                else:
                    cache_hits += 1
                prepared = folder / 'prepared.wav'
                convert_audio(cache, prepared, body['speed'])
                if event.is_set():
                    raise InterruptedError('Đã dừng.')
                pause = STYLES[body['style']]['pause_ms'] if index + 1 < len(chunks) else 0
                assembler.append(prepared, text, pause)
                if index == 0:
                    shutil.copyfile(prepared, folder / 'preview.wav')
                spoken_chars += len(text)
                elapsed = time.perf_counter() - started
                self.update(ident, completed_chunks=index+1, progress=(index+1)/len(chunks), cache_hits=cache_hits,
                    elapsed_seconds=elapsed, eta_seconds=elapsed/(index+1)*(len(chunks)-index-1),
                    preview_url='/download/'+ident+'/preview.wav')
            result = assembler.finish(); assembler = None
            if event.is_set():
                raise InterruptedError('Đã dừng.')
            elapsed = time.perf_counter()-started
            downloads = [{'name':name, 'url':'/download/'+ident+'/'+name} for name in result['parts']]
            report = {**result, 'id':ident, 'version':VERSION, 'language':body['language'], 'voice':body['voice'],
                'engine':('Microsoft Edge trực tuyến' if body['engine']=='edge' else ('VieNeu Turbo FP32' if body['language']=='VI' else 'MeloTTS CPU')),
                'model_load_seconds':total_load, 'processing_seconds':elapsed, 'realtime_multiplier':result['audio_seconds']/elapsed,
                'target_30x_verified':False, 'measurement':'Độ dài WAV (có khoảng nghỉ) / thời gian xử lý; không xác minh 30× lời đọc thực.',
                'cache_hits':cache_hits, 'total_chunks':len(chunks), 'fresh_inference':cache_hits==0,
                'source_audio_seconds':raw_seconds, 'speed':body['speed'], 'style':body['style'], 'warnings':document['warnings'],
                'subtitle_alignment':'Ranh giới từng đoạn tổng hợp, không căn từng từ.', 'downloads':downloads}
            atomic_json(folder / 'report.json', report)
            self.update(ident, **report, status='done', progress=1, eta_seconds=0,
                audio_url=downloads[0]['url'], bundle_url='/download/'+ident+'/all-files.zip',
                text_url='/download/'+ident+'/script.txt', srt_url='/download/'+ident+'/subtitles.srt',
                report_url='/download/'+ident+'/report.json')
        except InterruptedError:
            with self.lock:
                if self.jobs[ident]['status'] not in {'cancelled', 'interrupted'}:
                    self.jobs[ident].update(status='cancelled'); self.persist(self.jobs[ident])
        except Exception as error:
            with self.lock:
                if self.jobs[ident]['status'] not in {'cancelled', 'interrupted'}:
                    self.jobs[ident].update(status='error', error=str(error)[:1800]); self.persist(self.jobs[ident])
        finally:
            if assembler:
                assembler.close()
            for name in ('raw.wav', 'prepared.wav'):
                (folder / name).unlink(missing_ok=True)
            with self.condition:
                if slot is not None:
                    self.free_slots.add(slot)
                self.events.pop(ident, None); self.condition.notify_all()

    def cancel(self, ident=None, all_jobs=False):
        with self.condition:
            selected = list(self.jobs.values()) if all_jobs else [self.jobs.get(ident) if ident else self.job]
            for job in selected:
                if job and job['status'] in {'queued', 'running'}:
                    job['status'] = 'cancelled'; self.events[job['id']].set(); self.persist(job)
            # Close only readers currently owned by cancelled jobs: Reader.request receives
            # the job event and close below interrupts a blocking SDK/native call.
            for reader in list(self.readers.values()):
                owner = getattr(reader, 'owner', None)
                if owner in self.events and self.events[owner].is_set():
                    reader.close()
            self.condition.notify_all()
            return self.snapshot(self.jobs.get(ident) or self.job) if (ident in self.jobs if ident else self.job) else {'status':'idle'}

    def resume(self, ident):
        if not isinstance(ident,str) or not IDENT.fullmatch(ident):
            raise ValueError('Mã bản thu không hợp lệ.')
        with self.lock:
            if ident not in self.jobs or self.jobs[ident]['status'] not in TERMINAL:
                raise ValueError('Chỉ tiếp tục bản thu đã dừng/lỗi hoặc tạo lại bản đã xong.')
        source = self.root / 'outputs' / ident / 'input.json'
        if not source.is_file():
            raise ValueError('Bản thu cũ chưa lưu văn bản; nhập lại lời đọc để tạo bản mới.')
        body = json.loads(source.read_text(encoding='utf-8')); body['use_cache'] = True
        return self.start(body)


def handler(studio):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, content, mime='application/json; charset=utf-8'):
            data = json.dumps(content, ensure_ascii=False).encode() if isinstance(content,(dict,list)) else content
            self.send_response(status); self.send_header('Content-Type',mime); self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; media-src 'self'; frame-ancestors 'none'; base-uri 'self'")
            self.end_headers(); self.wfile.write(data)

        def allowed(self):
            host = self.headers.get('Host',''); origin = self.headers.get('Origin')
            return host.split(':')[0] in {'localhost','127.0.0.1'} and (origin is None or origin == 'http://'+host)

        def send_file(self, file, mime):
            size = file.stat().st_size; start = 0; end = size-1
            range_header = self.headers.get('Range')
            if range_header:
                match = re.fullmatch(r'bytes=(\d*)-(\d*)',range_header)
                if not match or not size:
                    return self.reply(416, {'error':'Khoảng tải không hợp lệ.'})
                left, right = match.groups()
                if left:
                    start = int(left); end = min(int(right),end) if right else end
                elif right and int(right)>0:
                    start = max(0,size-int(right))
                else:
                    return self.reply(416, {'error':'Khoảng tải không hợp lệ.'})
                if start>end:
                    return self.reply(416, {'error':'Khoảng tải không hợp lệ.'})
            self.send_response(206 if range_header else 200)
            self.send_header('Content-Type',mime); self.send_header('Content-Length',str(end-start+1))
            self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Accept-Ranges','bytes')
            self.send_header('Cache-Control','no-store')
            if range_header:
                self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
            if not file.name.endswith('.wav'):
                self.send_header('Content-Disposition','attachment; filename="'+file.name+'"')
            self.end_headers()
            with file.open('rb') as source:
                source.seek(start); left = end-start+1
                while left and (block:=source.read(min(65536,left))):
                    self.wfile.write(block); left -= len(block)

        def send_bundle(self, folder, ident):
            # Stream ZIP64 straight to the browser instead of duplicating hours of WAV on disk.
            names = sorted(p.name for p in folder.glob('part-*.wav')) + sorted(p.name for p in folder.glob('part-*.srt')) + ['script.txt','subtitles.srt','report.json']
            if (folder/'original.srt').is_file():
                names.append('original.srt')
            self.send_response(200); self.send_header('Content-Type','application/zip')
            self.send_header('Content-Disposition','attachment; filename="melo-viet-'+ident+'.zip"')
            self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Connection','close')
            self.end_headers()
            with zipfile.ZipFile(self.wfile, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
                for name in names:
                    archive.write(folder/name, arcname=name)
            self.close_connection = True

        def do_GET(self):
            if not self.allowed():
                return self.reply(403,{'error':'Chỉ truy cập từ máy cục bộ.'})
            path = urlsplit(self.path).path
            try:
                if path=='/':
                    return self.reply(200,Path(__file__).with_name('index.html').read_bytes(),'text/html; charset=utf-8')
                if path in {'/app.js','/style.css'}:
                    return self.reply(200,Path(__file__).with_name(path[1:]).read_bytes(),
                        'text/javascript; charset=utf-8' if path.endswith('.js') else 'text/css; charset=utf-8')
                if path=='/api/config':
                    return self.reply(200,{'languages':LABELS, 'styles':STYLES, 'offline':studio.offline,
                        'version':VERSION, 'max_characters':MAX_CHARS, 'parallelism':studio.parallelism,
                        'cpu_count':os.cpu_count(), 'local_installed':all((studio.root/'envs'/key/'bin/python').is_file() for key in ('melo','viet')), 'online_provider':'Microsoft Edge qua edge-tts (không phải API Azure chính thức)'})
                if path=='/api/jobs':
                    query = parse_qs(urlsplit(self.path).query)
                    limit = max(1,min(100,int(query.get('limit',['50'])[0]))); offset = max(0,int(query.get('offset',['0'])[0]))
                    return self.reply(200,studio.list_jobs(limit,offset))
                if path=='/api/job':
                    query = parse_qs(urlsplit(self.path).query)
                    with studio.lock:
                        job = studio.jobs.get(query.get('id',[''])[0]) if 'id' in query else studio.job
                        return self.reply(200,studio.snapshot(job) if job else {'status':'idle'})
                if re.fullmatch(r'/audio/[a-f0-9]{32}\.wav',path):
                    file = studio.root/'outputs'/path.rsplit('/',1)[1]
                    if file.is_file():
                        return self.send_file(file,'audio/wav')
                match = re.fullmatch(r'/download/([a-f0-9]{32})/(part-\d{4}\.(?:wav|srt)|preview\.wav|script\.txt|subtitles\.srt|original\.srt|report\.json|all-files\.zip)',path)
                if match:
                    ident, name = match.groups(); folder = studio.root/'outputs'/ident
                    with studio.lock:
                        job = studio.jobs.get(ident)
                        ready = job and (job['status']=='done' or name=='preview.wav')
                    if ready and name=='all-files.zip' and (folder/'report.json').is_file():
                        return self.send_bundle(folder, ident)
                    file = folder/name
                    if ready and file.is_file():
                        mime = ('audio/wav' if name.endswith('.wav') else 'application/json; charset=utf-8'
                                if name.endswith('.json') else 'application/x-subrip; charset=utf-8'
                                if name.endswith('.srt') else 'text/plain; charset=utf-8')
                        return self.send_file(file,mime)
                return self.reply(404,{'error':'Không tìm thấy.'})
            except (BrokenPipeError, ConnectionResetError):
                pass
            except (ValueError, OSError) as error:
                self.reply(422,{'error':str(error)[:600]})

        def do_POST(self):
            if not self.allowed():
                return self.reply(403,{'error':'Chỉ truy cập từ máy cục bộ.'})
            try:
                length = int(self.headers.get('Content-Length','0'))
                if not 0<length<=64*1024*1024:
                    raise ValueError('Yêu cầu rỗng hoặc quá 64 MB.')
                body = json.loads(self.rfile.read(length))
                if not isinstance(body,dict):
                    raise ValueError('Nội dung không hợp lệ.')
                if self.path=='/api/start':
                    return self.reply(202,studio.start(body))
                if self.path=='/api/batch':
                    return self.reply(202,{'jobs':studio.start_batch(body.get('jobs'))})
                if self.path=='/api/cancel':
                    return self.reply(200,studio.cancel(body.get('id'),bool(body.get('all'))))
                if self.path=='/api/resume':
                    return self.reply(202,studio.resume(body.get('id')))
                if self.path=='/api/settings':
                    return self.reply(200,studio.settings(body.get('parallelism')))
                if self.path=='/api/inspect':
                    document = parse_document(body.get('text'),body.get('name',''),body.get('format','auto'))
                    chunks = plan_document(document,body.get('chunk_size',480))
                    return self.reply(200,{'format':document['format'], 'characters':len(document['text']),
                        'chunks':len(chunks), 'cues':len(document['cues']), 'preview':document['text'][:500],
                        'warnings':document['warnings'], 'spoken_text':document['text'] if body.get('include_text') else None})
                self.reply(404,{'error':'Không tìm thấy.'})
            except (ValueError,TypeError,KeyError,AttributeError) as error:
                self.reply(422,{'error':str(error)[:1000]})

    return Handler


def main():
    p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,required=True)
    p.add_argument('--port',type=int,default=8817); p.add_argument('--offline',action='store_true'); a=p.parse_args()
    def stop(signum,frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,stop)
    if hasattr(signal,'SIGHUP'):
        signal.signal(signal.SIGHUP,stop)
    # Bind before touching history: a second launch must not mark live jobs interrupted.
    try:
        server=ThreadingHTTPServer(('127.0.0.1',a.port),BaseHTTPRequestHandler)
    except OSError as error:
        print(f'Không mở được cổng {a.port}. Đóng đúng cửa sổ tool cũ rồi thử lại. {error}',file=sys.stderr)
        raise SystemExit(1)
    import fcntl
    a.root.mkdir(parents=True,exist_ok=True)
    instance=(a.root/'.studio.lock').open('a')
    try:
        fcntl.flock(instance,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        instance.close();server.server_close()
        print('Thư mục dữ liệu đang được một cửa sổ tool khác sử dụng. Đóng cửa sổ đó trước.',file=sys.stderr)
        raise SystemExit(1)
    studio=Studio(a.root,a.offline); server.RequestHandlerClass=handler(studio)
    print(f'Melo + Việt Studio {VERSION}: http://localhost:{a.port} · giữ cửa sổ này mở.',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close(); studio.close(); instance.close()


if __name__=='__main__':
    main()
