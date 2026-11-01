"""Local seven-language UI. SDKs run in two separate persistent interpreters."""
import argparse
import atexit
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit

LABELS={'VI':'Việt · VieNeu Turbo','EN':'Anh · MeloTTS','FR':'Pháp · MeloTTS','JP':'Nhật · MeloTTS',
        'KR':'Hàn · MeloTTS','ES':'Tây Ban Nha · MeloTTS','ZH':'Trung · MeloTTS'}


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
                env=dict(os.environ,HF_HOME=str(self.root/'models/huggingface'),
                    HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',GRADIO_ANALYTICS_ENABLED='False',
                    OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='4',OMP_NUM_THREADS='4',PYTHONUNBUFFERED='1')
                if self.offline:env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
                self.process=subprocess.Popen([str(python),'-u',str(Path(__file__).with_name('worker.py'))],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,encoding='utf-8',env=env,start_new_session=True)
                process=self.process
                if cancel is not None and cancel.is_set():self.close();raise InterruptedError('Đã dừng.')
                ready=process.stdout.readline()
                if not ready or not json.loads(ready).get('ready'):raise RuntimeError('Không mở được bộ đọc. Xem logs trong thư mục cài.')
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
    def __init__(self,root,offline=False):
        self.root=Path(root);(self.root/'outputs').mkdir(parents=True,exist_ok=True)
        self.readers={key:Reader(root,key,offline) for key in ('melo','viet')}
        self.job=None;self.cancel_event=None;self.lock=threading.Lock();self.offline=offline
        atexit.register(self.close)

    def close(self):
        for reader in self.readers.values():reader.close()

    def validate(self,body):
        language=body.get('language');threads=body.get('threads',4)
        if language not in LABELS or type(threads) is not int or not 1<=threads<=16:raise ValueError('Kiểm tra ngôn ngữ và số luồng CPU.')
        return self.readers['viet' if language=='VI' else 'melo']

    def start(self,body):
        reader=self.validate(body)
        op=body.get('op')
        if op not in {'voices','render'}:raise ValueError('Thao tác không hợp lệ.')
        if op=='render' and (not isinstance(body.get('text'),str) or not body['text'].strip() or len(body['text'])>100000):
            raise ValueError('Nhập 1–100.000 ký tự lời đọc.')
        ident=uuid.uuid4().hex
        payload={key:body[key] for key in ('language','threads','voice','text') if key in body}
        payload.update(op=op,output=str(self.root/'outputs'/(ident+'.wav')))
        with self.lock:
            if self.job and self.job['status']=='running':raise ValueError('Đang xử lý tác vụ trước. Chờ xong hoặc bấm Dừng.')
            cancelled=threading.Event();self.cancel_event=cancelled
            self.job={'id':ident,'status':'running','op':op,'language':body['language']}
        def work():
            started=time.perf_counter()
            try:
                result=reader.request(payload,cancelled)
                elapsed=time.perf_counter()-started
                with self.lock:
                    if self.job['id']!=ident or self.job['status']=='cancelled':return
                    public={k:v for k,v in result.items() if k not in {'ok'}}
                    if op=='render':
                        public.update(processing_seconds=elapsed,audio_url='/audio/'+ident+'.wav',
                            realtime_multiplier=result['audio_seconds']/elapsed,target_30x_verified=False,
                            measurement='Độ dài WAV (có khoảng nghỉ) / thời gian yêu cầu. Chưa xác minh 30× lời đọc thực.')
                        (self.root/'outputs'/(ident+'.json')).write_text(json.dumps(public,ensure_ascii=False,indent=2),encoding='utf-8')
                    self.job.update(status='done',**public)
            except Exception as error:
                with self.lock:
                    if self.job['id']==ident and self.job['status']!='cancelled':self.job.update(status='error',error=str(error)[:1600])
        threading.Thread(target=work,daemon=True).start()
        return dict(self.job)

    def cancel(self):
        with self.lock:
            if self.job and self.job['status']=='running':
                self.job['status']='cancelled'
                self.cancel_event.set()
                self.readers['viet' if self.job['language']=='VI' else 'melo'].close()
        return self.job or {'status':'idle'}


def handler(studio):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,status,content,mime='application/json; charset=utf-8'):
            data=json.dumps(content,ensure_ascii=False).encode() if isinstance(content,(dict,list)) else content
            self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; media-src 'self'; frame-ancestors 'none'; base-uri 'self'")
            self.end_headers();self.wfile.write(data)
        def allowed(self):
            host=self.headers.get('Host','')
            origin=self.headers.get('Origin')
            return host.split(':')[0] in {'localhost','127.0.0.1'} and (origin is None or origin=='http://'+host)
        def do_GET(self):
            if not self.allowed():return self.reply(403,{'error':'Chỉ truy cập từ máy cục bộ.'})
            path=urlsplit(self.path).path
            if path=='/':return self.reply(200,Path(__file__).with_name('index.html').read_bytes(),'text/html; charset=utf-8')
            if path in {'/app.js','/style.css'}:
                return self.reply(200,Path(__file__).with_name(path[1:]).read_bytes(),'text/javascript; charset=utf-8' if path.endswith('.js') else 'text/css; charset=utf-8')
            if path=='/api/config':return self.reply(200,{'languages':LABELS,'offline':studio.offline,'version':'1.0.0'})
            if path=='/api/job':
                with studio.lock:return self.reply(200,dict(studio.job) if studio.job else {'status':'idle'})
            if re.fullmatch(r'/audio/[a-f0-9]{32}\.wav',path):
                file=studio.root/'outputs'/path.rsplit('/',1)[1]
                if file.is_file():
                    self.send_response(200);self.send_header('Content-Type','audio/wav');self.send_header('Content-Length',str(file.stat().st_size));self.send_header('X-Content-Type-Options','nosniff');self.end_headers()
                    with file.open('rb') as source:
                        while block:=source.read(65536):self.wfile.write(block)
                    return
            self.reply(404,{'error':'Không tìm thấy.'})
        def do_POST(self):
            if not self.allowed():return self.reply(403,{'error':'Chỉ truy cập từ máy cục bộ.'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=1024*1024:raise ValueError('Yêu cầu quá lớn hoặc rỗng.')
                body=json.loads(self.rfile.read(length))
                if not isinstance(body,dict):raise ValueError('Nội dung không hợp lệ.')
                if self.path=='/api/start':return self.reply(202,studio.start(body))
                if self.path=='/api/cancel':return self.reply(200,studio.cancel())
                self.reply(404,{'error':'Không tìm thấy.'})
            except (ValueError,TypeError,KeyError) as error:self.reply(422,{'error':str(error)})
    return Handler


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--port',type=int,default=8817);p.add_argument('--offline',action='store_true');a=p.parse_args()
    def stop(signum,frame):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,stop)
    if hasattr(signal,'SIGHUP'):signal.signal(signal.SIGHUP,stop)
    studio=Studio(a.root,a.offline);server=ThreadingHTTPServer(('127.0.0.1',a.port),handler(studio))
    print(f'Melo + Việt: http://localhost:{a.port} · giữ cửa sổ này mở.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close();studio.close()

if __name__=='__main__':main()
