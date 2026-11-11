from __future__ import annotations
import queue,threading,time,ctypes,os
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from PIL import Image,ImageTk,ImageOps
from .common import Context,binary,signature
from .framing import pointer_in_image

def scene_preview(p,index,ctx):
    from .render import render_shot,source_audio
    shots=p['plan']['shots'];s=shots[index];video=render_shot(p,s,shots[index-1] if index else None,ctx,resolution=360,preview=True)
    fps=p['plan']['fps'];a=s['start_frame']/fps;d=s['frames']/fps
    key=signature({'version':2,'voice':p['voice_sha256'],'a':a,'d':d,'mute':p['settings']['mute_source'],'volume':p['settings']['source_volume'],'shot':s})[:18];audio=Path(p['job'])/'preview_cache'/f'audio_{key}.wav'
    if not audio.exists():
        cmd=[binary('ffmpeg'),'-nostdin','-v','error','-y','-ss',str(a),'-i',p['voice_wav']]
        mixed=not p['settings']['mute_source'] and p['settings']['source_volume']>0
        if mixed:
            cmd+=['-i',source_audio(p,s,ctx),'-filter_complex',f'[1:a]volume={p["settings"]["source_volume"]}[src];[0:a][src]amix=inputs=2:duration=first:normalize=0[a]','-map','[a]']
        else:cmd+=['-map','0:a:0']
        cmd+=['-t',str(d),'-ac','1','-ar','48000','-c:a','pcm_s16le',audio];ctx.run(cmd,log=audio.with_suffix('.log'))
    return str(video),str(audio),d

class Player(ttk.Frame):
    """Local video surface, seek and WAV playback; decoding stays off Tk's thread."""
    def __init__(self,master,on_focus=None):
        super().__init__(master);self.on_focus=on_focus;self.path=None;self.audio=None;self.duration=0.;self.position=0.;self.active=False;self.generation=0;self.q=queue.Queue(maxsize=3);self._photo=None;self.alias=f'autodoc{id(self)}'
        self.canvas=tk.Canvas(self,bg='#111823',height=300,highlightthickness=0);self.canvas.pack(fill='both',expand=True);self.canvas.create_text(300,140,text='Chọn cảnh để xem trước',fill='white');self.canvas.bind('<Button-1>',self.focus_at)
        self._image_box=None;self.video_width=0;self.video_height=0
        bar=ttk.Frame(self);bar.pack(fill='x');ttk.Button(bar,text='▶ Phát / ⏸ Dừng',command=self.toggle).pack(side='left');self.caption=ttk.Label(bar,text='0.00 / 0.00s');self.caption.pack(side='right')
        self.scale=ttk.Scale(self,from_=0,to=1);self.scale.pack(fill='x');self.scale.bind('<ButtonPress-1>',lambda e:self.stop());self.scale.bind('<ButtonRelease-1>',lambda e:self.seek(float(self.scale.get())))
        self.after(30,self.poll);self.bind('<Destroy>',self.cleanup,add='+')
    def mci(self,command):
        if os.name=='nt':return ctypes.windll.winmm.mciSendStringW(command,None,0,None)
        return 0
    def focus_at(self,event):
        point=pointer_in_image(event.x,event.y,self._image_box)
        if self.on_focus and point:self.on_focus(*point)
    def cleanup(self,event=None):
        if event is None or event.widget is self:self.stop();self.mci(f'close {self.alias}')
    def stop(self):
        self.active=False;self.generation+=1;self.mci(f'stop {self.alias}')
    def load(self,path,audio=None,duration=None):
        self.stop();self.mci(f'close {self.alias}');self.path=str(path);self.audio=audio;self._image_box=None
        import av
        with av.open(self.path) as c:
            stream=c.streams.video[0];self.video_width=stream.width;self.video_height=stream.height;self.duration=float(duration or (c.duration/1000000 if c.duration else stream.duration*stream.time_base))
        if audio:self.mci(f'open "{audio}" type waveaudio alias {self.alias}')
        self.scale.configure(to=max(.01,self.duration));self.seek(0)
    def seek(self,value):
        self.stop();self.position=max(0,min(value,max(0,self.duration-.001)));self.scale.set(self.position);self.caption.configure(text=f'{self.position:.2f} / {self.duration:.2f}s');self.start_decode(False)
    def toggle(self):
        if self.active:self.stop();return
        if not self.path:return
        if self.position>=self.duration-.08:self.position=0
        self.stop();self.active=True
        if self.audio:self.mci(f'play {self.alias} from {round(self.position*1000)}')
        self.start_decode(True)
    def start_decode(self,playing):
        generation=self.generation;path=self.path;start=self.position
        if not path:return
        def put(value):
            while generation==self.generation:
                try:self.q.put((generation,*value),timeout=.05);return True
                except queue.Full:pass
            return False
        def decode():
            import av
            try:
                with av.open(path) as c:
                    stream=c.streams.video[0];c.seek(round(start*1000000),backward=True);base=time.monotonic();last=-1
                    for frame in c.decode(stream):
                        t=float(frame.time or 0)
                        if t<start-.04:continue
                        if generation!=self.generation:return
                        if playing and t-last<1/15:continue
                        last=t
                        if playing:
                            delay=(t-start)-(time.monotonic()-base)
                            while delay>.005 and generation==self.generation:time.sleep(min(.02,delay));delay=(t-start)-(time.monotonic()-base)
                        im=frame.to_image();im.thumbnail((960,540))
                        if not put(('frame',t,im)):return
                        if not playing:return
                if playing:put(('end',self.duration,None))
            except Exception as e:put(('error',0,str(e)))
        threading.Thread(target=decode,daemon=True).start()
    def poll(self):
        try:
            while True:
                g,kind,t,im=self.q.get_nowait()
                if g!=self.generation:continue
                if kind=='frame':
                    self.position=t;w=max(2,self.canvas.winfo_width());h=max(2,self.canvas.winfo_height());im=ImageOps.contain(im,(w,h));self._image_box=((w-im.width)/2,(h-im.height)/2,im.width,im.height);self._photo=ImageTk.PhotoImage(im);self.canvas.delete('all');self.canvas.create_image(w/2,h/2,image=self._photo);self.scale.set(t);self.caption.configure(text=f'{t:.2f} / {self.duration:.2f}s')
                elif kind=='end':self.active=False;self.position=self.duration;self.mci(f'stop {self.alias}')
                elif kind=='error':self.caption.configure(text='Không đọc được preview: '+im[:80])
        except queue.Empty:pass
        if self.winfo_exists():self.after(30,self.poll)
