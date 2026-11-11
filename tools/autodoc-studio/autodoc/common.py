from __future__ import annotations
import hashlib,json,os,shutil,subprocess,sys,threading,time
from pathlib import Path
from typing import Callable

def console_notify(pct,msg):
    text=f'{pct:5.1f}% {msg}'
    try:print(text,flush=True)
    except UnicodeEncodeError:
        encoding=getattr(sys.stdout,'encoding',None) or 'utf-8'
        print(text.encode(encoding,errors='backslashreplace').decode(encoding),flush=True)

class Cancelled(Exception): pass

class Context:
    def __init__(self, notify: Callable | None = None, cancel: threading.Event | None = None):
        self.notify = notify or console_notify
        self.cancel = cancel or threading.Event()
    def check(self):
        if self.cancel.is_set(): raise Cancelled('Đã dừng; giữ cache để tiếp tục lần sau.')
    def emit(self, pct, msg):
        self.check(); self.notify(float(pct), str(msg))
    def run(self, args, *, log: Path | None = None, capture=False, cwd=None):
        self.check()
        # No shell: filenames are always arguments, never executable expressions.
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        if capture:
            import tempfile
            with tempfile.TemporaryFile() as stream:
                p = subprocess.Popen([str(x) for x in args], stdout=stream, stderr=subprocess.PIPE,
                                     creationflags=flags,cwd=cwd)
                while True:
                    try: _, error = p.communicate(timeout=.25); break
                    except subprocess.TimeoutExpired:
                        if self.cancel.is_set():
                            p.terminate()
                            try: p.communicate(timeout=3)
                            except subprocess.TimeoutExpired: p.kill(); p.communicate()
                            raise Cancelled('Đã dừng tiến trình.')
                if p.returncode: raise RuntimeError(error.decode('utf-8', errors='replace')[-2400:])
                stream.seek(0); return stream.read()
        log = log or Path(os.devnull)
        with log.open('wb') as stream:
            p = subprocess.Popen([str(x) for x in args], stdout=stream, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, creationflags=flags,cwd=cwd)
            while p.poll() is None:
                if self.cancel.is_set():
                    p.terminate()
                    try: p.wait(timeout=3)
                    except subprocess.TimeoutExpired: p.kill(); p.wait()
                    raise Cancelled('Đã dừng tiến trình.')
                time.sleep(.15)
        if p.returncode:
            detail = log.read_text(encoding='utf-8',errors='replace')[-2500:] if log != Path(os.devnull) else ''
            raise RuntimeError(f'Lệnh thất bại ({Path(str(args[0])).name}): {detail}')

def root_dir():
    return Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent

def data_dir():
    base = Path(os.environ.get('LOCALAPPDATA', Path.home()/'.cache')) / 'AutoDocStudio'
    base.mkdir(parents=True, exist_ok=True); return base

def binary(name):
    ext = '.exe' if os.name == 'nt' else ''
    for p in [data_dir()/'bin'/f'{name}{ext}',root_dir()/'bin'/f'{name}{ext}', Path(getattr(sys,'_MEIPASS',root_dir()))/'bin'/f'{name}{ext}']:
        if p.is_file(): return str(p)
    p = shutil.which(name)
    if not p: raise RuntimeError(f'Thiếu {name}. Dùng bản Windows trọn gói hoặc cài FFmpeg và thêm vào PATH.')
    return p

def digest(path: Path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def signature(value): return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def save_json(path: Path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)

def probe(path: Path, ctx: Context):
    return json.loads(ctx.run([binary('ffprobe'),'-v','error','-show_streams','-show_format','-of','json',path],capture=True))

def valid_input(path: Path):
    p=path.expanduser().resolve()
    if not p.is_file(): raise ValueError(f'Không tìm thấy tệp: {p}')
    return p

def srt(cues):
    def stamp(t):
        ms=round(t*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);sec,ms=divmod(ms,1000)
        return f'{h:02}:{m:02}:{sec:02},{ms:03}'
    return '\n\n'.join(f'{i}\n{stamp(x["start"])} --> {stamp(x["end"])}\n{x["text"].strip()}' for i,x in enumerate(cues,1))+'\n'
