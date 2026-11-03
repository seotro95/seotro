"""Lazy, cancellable MP3 export. WAV synthesis and its measurements are unchanged."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import threading
import time
import wave
from timing import measure_encoded


class Exports:
    def __init__(self, studio):
        self.studio=studio;self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='mp3-export')
        self.events={};self.processes={};self.closed=False
        for job in studio.jobs.values():
            if job.get('mp3_status') in {'queued','running'}:
                job.update(mp3_status='interrupted',mp3_error='Xuất MP3 bị gián đoạn; WAV vẫn được giữ. Bấm Tạo MP3 để tiếp tục.')
                studio.persist(job)

    def update(self, ident, **fields):
        with self.studio.lock:
            job=self.studio.jobs[ident];job.update(fields);self.studio.persist(job)

    def start(self, ident):
        if not isinstance(ident,str) or not re.fullmatch(r'[a-f0-9]{32}',ident):
            raise ValueError('Mã bản thu không hợp lệ.')
        with self.studio.lock:
            job=self.studio.jobs.get(ident)
            if not job or job.get('status')!='done' or job.get('op')!='render':
                raise ValueError('Tạo xong bản WAV trước khi xuất MP3.')
            if self.closed:raise ValueError('Tool đang đóng.')
            if job.get('mp3_status') in {'queued','running','done'}:
                if job.get('mp3_status')!='done' or (self.studio.root/'outputs'/ident/'voice.mp3').is_file():
                    return self.studio.snapshot(job)
            if len(self.events)>=16:raise ValueError('Đang chờ xuất quá nhiều MP3; vui lòng chờ bớt.')
            self.events[ident]=threading.Event()
            self.update(ident,mp3_status='queued',mp3_progress=0,mp3_error=None)
            self.pool.submit(self.work,ident,self.events[ident])
            return self.studio.snapshot(job)

    def stop(self, ident):
        with self.studio.lock:
            event=self.events.get(ident)
            if event:
                event.set();self.update(ident,mp3_status='cancelled',mp3_error='Đã dừng xuất MP3; WAV vẫn còn.')
            process=self.processes.get(ident)
        if process and process.poll() is None:
            try:os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        return self.studio.snapshot(self.studio.jobs[ident]) if ident in self.studio.jobs else {'mp3_status':'idle'}

    def work(self, ident, event):
        folder=self.studio.root/'outputs'/ident;folder.mkdir(parents=True,exist_ok=True)
        temporary=folder/'voice.partial.mp3';listing=folder/'mp3-inputs.ffconcat';started=time.perf_counter();process=None
        try:
            if event.is_set():raise InterruptedError('Đã dừng xuất MP3.')
            with self.studio.lock:
                legacy=self.studio.jobs[ident].get('legacy',False)
                timed=self.studio.jobs[ident].get('timing_mode')=='exact'
            export_rate=24000 if timed else 44100
            files=([self.studio.root/'outputs'/(ident+'.wav')] if legacy else
                   sorted(p for p in folder.glob('part-*.wav') if re.fullmatch(r'part-\d{4}\.wav',p.name)))
            if not files:raise ValueError('Không tìm thấy WAV của bản thu.')
            total=0;signature=None
            for file in files:
                with wave.open(str(file),'rb') as source:
                    params=source.getparams()[:3]
                    if signature is not None and signature!=params:raise ValueError('Các phần WAV khác định dạng; chưa ghép MP3.')
                    signature=params;total+=source.getnframes()/source.getframerate()
            if not total:raise ValueError('WAV không có âm thanh.')
            # ffconcat quoting, not a shell command; no external protocol is allowed.
            listing.write_text('ffconcat version 1.0\n'+''.join("file '"+str(p.resolve()).replace("'","'\\''")+"'\n" for p in files),encoding='utf-8')
            self.update(ident,mp3_status='running',mp3_progress=0)
            command=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-f','concat','-safe','0',
                '-protocol_whitelist','file,pipe','-i',str(listing),'-map','0:a:0','-map_metadata','-1',
                '-c:a','libmp3lame','-b:a','192k','-ar',str(export_rate),'-ac','1','-threads','1',
                '-progress','pipe:1','-nostats',str(temporary)]
            with (folder/'mp3-encode.log').open('w',encoding='utf-8') as log:
                process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=log,text=True,encoding='utf-8',start_new_session=True)
                with self.studio.lock:self.processes[ident]=process
                if event.is_set():
                    try:os.killpg(process.pid,signal.SIGTERM)
                    except ProcessLookupError:pass
                previous=0
                for line in process.stdout:
                    if line.startswith('out_time='):
                        try:
                            h,m,s=map(float,line.strip().split('=',1)[1].split(':'));done=h*3600+m*60+s
                            progress=max(previous,min(.99,done/total));previous=progress
                            if not event.is_set():self.update(ident,mp3_progress=progress)
                        except ValueError:pass
                code=process.wait()
            if event.is_set():raise InterruptedError('Đã dừng xuất MP3.')
            if code or not temporary.is_file() or temporary.stat().st_size<64:
                detail=(folder/'mp3-encode.log').read_text(encoding='utf-8',errors='replace')[-600:]
                raise ValueError('Không xuất được MP3; WAV vẫn còn. '+detail)
            actual=measure_encoded(temporary,folder,export_rate,round(total*export_rate) if timed else None,event)
            if event.is_set():raise InterruptedError('Đã dừng xuất MP3.')
            temporary.replace(folder/'voice.mp3')
            info={'format':'MP3','codec':'libmp3lame','bitrate':192000,'sample_rate':export_rate,'actual_audio_seconds':actual['audio_seconds'],'duration_verified':True,'duration_report':actual,
                  'source_audio_seconds':total,'encoding_seconds':time.perf_counter()-started,
                  'created_at':datetime.now(timezone.utc).isoformat(),'source_parts':len(files)}
            (folder/'mp3-report.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
            self.update(ident,mp3_status='done',mp3_progress=1,mp3_url='/download/'+ident+'/voice.mp3',
                        mp3_encoding_seconds=info['encoding_seconds'],mp3_audio_seconds=actual['audio_seconds'],mp3_duration_verified=True,mp3_error=None)
        except InterruptedError:
            with self.studio.lock:
                if self.studio.jobs[ident].get('mp3_status')!='interrupted':self.update(ident,mp3_status='cancelled')
        except Exception as error:
            self.update(ident,mp3_status='error',mp3_error=str(error)[:1000])
        finally:
            if process and process.poll() is None:
                try:os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                try:process.wait(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3)
            temporary.unlink(missing_ok=True);listing.unlink(missing_ok=True)
            with self.studio.lock:self.events.pop(ident,None);self.processes.pop(ident,None)

    def close(self):
        with self.studio.lock:
            if self.closed:return
            self.closed=True
            for ident,event in self.events.items():
                event.set();self.update(ident,mp3_status='interrupted',mp3_error='Tool đã đóng; bấm Tạo MP3 khi mở lại. WAV vẫn còn.')
            processes=list(self.processes.values())
        for process in processes:
            if process.poll() is None:
                try:os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError:pass
        self.pool.shutdown(wait=False,cancel_futures=True)
