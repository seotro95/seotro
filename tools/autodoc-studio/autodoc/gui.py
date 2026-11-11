from __future__ import annotations
import copy,json,os,queue,threading,traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,colorchooser,font
from .common import Context,Cancelled,data_dir,save_json
from .project import DEFAULTS,options,load,save,split,merge_previous,swap_sources
from .subtitles import export,read_srt,read_txt,align_txt,validate,seconds
from .effects import NAMES,TRANSITION_NAMES,TRANSITIONS,installed_effects,install_pack
from .player import Player,scene_preview
from .languages import LABELS

class App(tk.Tk):
    def __init__(self):
        super().__init__();self.title('AutoDoc Studio 2.3 — Edit ngang 16:9 / dọc 9:16');screen_w=max(800,self.winfo_screenwidth()-60);screen_h=max(600,self.winfo_screenheight()-80);self.geometry(f'{min(1360,screen_w)}x{min(950,screen_h)}');self.minsize(min(1080,screen_w),min(720,screen_h));self.p=None;self.busy=False;self.cancel=threading.Event();self.queue=queue.Queue();self.last_export='';self.last_auto_result=None;self.selected=0;self.preview_pending=None
        self.vars={};self.edit={};self.cuevars={};self.preferences=data_dir()/'preferences_v2.json'
        self.voice=tk.StringVar();self.media=tk.StringVar();self.output=tk.StringVar(value=str(Path.home()/'Videos'/'AutoDocStudio'));self.subpath=tk.StringVar();self.visualpath=tk.StringVar();self.status=tk.StringVar(value='Chọn voice và thư mục ảnh/video → TỰ ĐỘNG EDIT & XUẤT. Hoặc Tự xếp cảnh để sửa trước khi xuất.')
        self.stylevars={k:(tk.BooleanVar(value=v) if isinstance(v,bool) else tk.StringVar(value=str(v))) for k,v in DEFAULTS['subtitle_style'].items()}
        for k,v in DEFAULTS.items():
            if k in ['subtitle_style','clip_model_path','whisper_model_path','subtitle_path','visual_script_path']:continue
            self.vars[k]=tk.BooleanVar(value=v) if isinstance(v,bool) else tk.StringVar(value=str(v))
        self.build();self.protocol('WM_DELETE_WINDOW',self.close);self.after(60,self.poll)
        if self.preferences.exists():
            try:
                pref=json.loads(self.preferences.read_text(encoding='utf-8-sig'));self.output.set(pref.get('output',self.output.get()));self.last_project=pref.get('last_project','')
            except Exception:self.last_project=''
    def file_row(self,parent,label,var,kind='file',types=None):
        row=ttk.Frame(parent);row.pack(fill='x',pady=2);ttk.Label(row,text=label,width=16).pack(side='left');ttk.Entry(row,textvariable=var).pack(side='left',fill='x',expand=True)
        def choose():
            path=filedialog.askdirectory() if kind=='dir' else filedialog.askopenfilename(filetypes=types or [('Tất cả','*.*')])
            if path:var.set(path)
        ttk.Button(row,text='Chọn…',width=8,command=choose).pack(side='left',padx=4)
    def combo(self,parent,label,var,values,width=21):
        row=ttk.Frame(parent);row.pack(fill='x',pady=3);ttk.Label(row,text=label,width=20).pack(side='left');box=ttk.Combobox(row,textvariable=var,values=values,state='readonly',width=width);box.pack(side='left',fill='x',expand=True);return box
    def entry(self,parent,label,var,width=20):
        row=ttk.Frame(parent);row.pack(fill='x',pady=3);ttk.Label(row,text=label,width=20).pack(side='left');ttk.Entry(row,textvariable=var,width=width).pack(side='left',fill='x',expand=True)
    def button(self,parent,text,command):return ttk.Button(parent,text=text,command=lambda:self.safe(command))
    def build(self):
        top=ttk.LabelFrame(self,text='Đầu vào');top.pack(fill='x',padx=10,pady=5)
        self.file_row(top,'Voice chính',self.voice,types=[('Âm thanh','*.wav *.mp3 *.m4a *.flac *.aac *.ogg'),('Tất cả','*.*')]);self.file_row(top,'Ảnh / video',self.media,'dir');self.file_row(top,'Nơi lưu dự án',self.output,'dir');self.file_row(top,'Phụ đề (tùy chọn)',self.subpath,types=[('TXT / SRT','*.txt *.srt')])
        self.file_row(top,'Tham chiếu Anh',self.visualpath,types=[('English TXT / SRT (tùy chọn)','*.txt *.srt')])
        ratio_row=ttk.Frame(top);ratio_row.pack(fill='x',pady=3);ttk.Label(ratio_row,text='Tỷ lệ video',width=16).pack(side='left');ratio_box=ttk.Combobox(ratio_row,textvariable=self.vars['aspect_ratio'],values=['16:9','9:16'],state='readonly',width=9);ratio_box.pack(side='left');ttk.Label(ratio_row,text=' 16:9 ngang • 9:16 dọc. Chọn trước khi tự động edit hoặc xuất.').pack(side='left');ratio_box.bind('<<ComboboxSelected>>',lambda e:self.apply_settings() if self.p and not self.busy else None)
        auto=ttk.Frame(self);auto.pack(fill='x',padx=10,pady=3);ttk.Style(self).configure('Auto.TButton',font=('Segoe UI',10,'bold'),padding=(10,6))
        self.auto_button=ttk.Button(auto,text='TỰ ĐỘNG EDIT & XUẤT',style='Auto.TButton',command=lambda:self.safe(self.auto_edit));self.auto_button.pack(side='left')
        ttk.Label(auto,text='Một lần bấm: tự xếp cảnh, ghép voice, áp dụng logo/phụ đề và lưu video.').pack(side='left',padx=10)
        ttk.Button(auto,text='Dừng tác vụ',command=lambda:self.cancel.set()).pack(side='right')
        bar=ttk.Frame(self);bar.pack(fill='x',padx=10)
        for text,fn in [('① Tự xếp cảnh',self.analyze),('Mở dự án',self.open_project),('Lưu dự án',self.save_project),('② Xuất video…',self.export_dialog),('Mở video đã xuất',self.open_result)]:self.button(bar,text,fn).pack(side='left',padx=3,pady=4)
        area=ttk.Panedwindow(self,orient='horizontal');area.pack(fill='both',expand=True,padx=10,pady=5)
        left=ttk.Frame(area);right=ttk.Frame(area,width=405);area.add(left,weight=3);area.add(right,weight=2)
        self.player=Player(left,on_focus=self.set_focus);self.player.pack(fill='both',expand=True)
        ttk.Label(left,text='Bấm lên hình để đặt tâm cắt. Preview phát cảnh đang chọn, kèm đúng đoạn voice.',foreground='#526171').pack(anchor='w')
        treeframe=ttk.Frame(left);treeframe.pack(fill='both',expand=True)
        self.timeline=ttk.Treeview(treeframe,columns=('time','source','effect','score'),show='headings',height=7)
        for k,title,w in [('time','Mốc / giây',120),('source','Ảnh / video',280),('effect','Hiệu ứng',100),('score','AI',50)]:self.timeline.heading(k,text=title);self.timeline.column(k,width=w,minwidth=40)
        scroll=ttk.Scrollbar(treeframe,orient='vertical',command=self.timeline.yview);self.timeline.configure(yscrollcommand=scroll.set);self.timeline.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y');self.timeline.bind('<<TreeviewSelect>>',self.select_scene)
        self.timeline.tag_configure('review',background='#fff1cc',foreground='#714100')
        notebook=ttk.Notebook(right);notebook.pack(fill='both',expand=True)
        def tab(title):
            shell=ttk.Frame(notebook);notebook.add(shell,text=title);canvas=tk.Canvas(shell,highlightthickness=0);scroll=ttk.Scrollbar(shell,orient='vertical',command=canvas.yview);canvas.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True);body=ttk.Frame(canvas,padding=8);item=canvas.create_window((0,0),window=body,anchor='nw');body.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')));canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width));return body
        edit=tab('Cảnh');subs=tab('Phụ đề');brand=tab('Logo / tiếng');config=tab('AI / xuất')
        for k,v in [('source_id',''),('source_in','0'),('speed','1'),('crop','1'),('focus_x','.5'),('focus_y','.5'),('effect','none'),('transition','cut')]:self.edit[k]=tk.StringVar(value=v)
        self.sourcebox=self.combo(edit,'Nguồn cảnh',self.edit['source_id'],[])
        self.entry(edit,'Lấy từ giây',self.edit['source_in']);self.entry(edit,'Tốc độ (0.25–3)',self.edit['speed']);self.entry(edit,'Phóng/cắt (1–2)',self.edit['crop']);self.entry(edit,'Tâm ngang (0–1)',self.edit['focus_x']);self.entry(edit,'Tâm dọc (0–1)',self.edit['focus_y'])
        self.effectbox=self.combo(edit,'Hiệu ứng',self.edit['effect'],[]);self.transitionbox=self.combo(edit,'Chuyển cảnh vào',self.edit['transition'],[f'{k} | {TRANSITION_NAMES[k]}' for k in TRANSITIONS])
        self.refresh_effects();self.button(edit,'Áp dụng và xem trước',self.apply_scene).pack(fill='x',pady=5)
        row=ttk.Frame(edit);row.pack(fill='x')
        for t,fn in [('↑ Đổi nguồn',lambda:self.move(-1)),('↓ Đổi nguồn',lambda:self.move(1)),('Chia tại con trỏ',self.split_scene),('Gộp cảnh trước',self.merge_scene)]:self.button(row,t,fn).pack(fill='x',pady=2)
        self.scene_text=tk.Text(edit,height=3,wrap='word');self.scene_text.pack(fill='x',pady=6)
        self.button(edit,'Tải gói hiệu ứng bổ sung',self.get_pack).pack(fill='x')
        self.cuetree=ttk.Treeview(subs,columns=('time','text'),show='headings',height=5);self.cuetree.heading('time',text='Thời gian');self.cuetree.heading('text',text='Lời');self.cuetree.column('time',width=100);self.cuetree.column('text',width=210);self.cuetree.pack(fill='both',expand=True);self.cuetree.bind('<<TreeviewSelect>>',self.select_cue)
        for k in ['start','end']:self.cuevars[k]=tk.StringVar(value='0');self.entry(subs,'Bắt đầu (s)' if k=='start' else 'Kết thúc (s)',self.cuevars[k])
        self.cuetext=tk.Text(subs,height=3,wrap='word');self.cuetext.pack(fill='x');row=ttk.Frame(subs);row.pack(fill='x')
        for t,fn in [('Sửa lời',self.apply_cue),('Thêm',self.add_cue),('Xóa',self.delete_cue),('Nhập',self.import_subs),('Xuất',self.export_subs)]:self.button(row,t,fn).pack(side='left',padx=1,pady=4)
        self.combo(subs,'Hiện phụ đề',self.vars['subtitle_mode'],['none','burn','soft']);ttk.Label(subs,text='burn: màu/phông ghi vào hình • soft: bật/tắt trong trình phát',wraplength=390).pack(anchor='w')
        fonts=sorted(set(font.families()))
        row=ttk.Frame(subs);row.pack(fill='x');ttk.Label(row,text='Phông chữ',width=20).pack(side='left');ttk.Combobox(row,textvariable=self.stylevars['font'],values=fonts,width=21).pack(fill='x',expand=True)
        self.entry(subs,'Cỡ chữ (ở 720p)',self.stylevars['size']);self.entry(subs,'Độ dày viền',self.stylevars['outline']);self.combo(subs,'Vị trí',self.stylevars['position'],['bottom','middle','top'])
        colors=ttk.Frame(subs);colors.pack(fill='x')
        for k,t in [('color','Màu chữ'),('outline_color','Màu viền'),('background_color','Màu nền')]:self.button(colors,t,lambda key=k:self.pick_color(key)).pack(side='left',padx=3)
        row=ttk.Frame(subs);row.pack(fill='x')
        for k,t in [('bold','Đậm'),('italic','Nghiêng'),('background','Hộp nền')]:ttk.Checkbutton(row,text=t,variable=self.stylevars[k]).pack(side='left')
        self.button(subs,'Áp dụng kiểu / xem trước',self.apply_settings).pack(fill='x',pady=5)
        self.file_row(brand,'Logo PNG/JPG',self.vars['logo_path'],types=[('Ảnh','*.png *.jpg *.webp *.bmp')]);self.combo(brand,'Vị trí logo',self.vars['logo_position'],['top_left','top_right','bottom_left','bottom_right','center']);self.entry(brand,'Rộng logo (% hình)',self.vars['logo_size']);self.entry(brand,'Độ hiện (0–1)',self.vars['logo_opacity'])
        ttk.Label(brand,text='Để trống đường dẫn để bỏ logo. PNG hỗ trợ nền trong suốt.',wraplength=370).pack(anchor='w',pady=5)
        ttk.Checkbutton(brand,text='Tắt âm thanh clip gốc (chỉ giữ voice)',variable=self.vars['mute_source']).pack(anchor='w',pady=8);self.entry(brand,'Âm lượng clip (0–1)',self.vars['source_volume']);ttk.Label(brand,text='Bỏ chọn để trộn tiếng clip với voice. Ảnh tự có tiếng nền im lặng.',wraplength=380).pack(anchor='w');self.button(brand,'Áp dụng logo / tiếng',self.apply_settings).pack(fill='x',pady=8)
        self.combo(config,'Tỷ lệ video',self.vars['aspect_ratio'],['16:9','9:16']);self.combo(config,'Độ nét (cạnh ngắn)',self.vars['resolution'],[720,1080]);self.combo(config,'Khung/giây',self.vars['fps'],[24,25,30,60]);self.combo(config,'Mã hóa',self.vars['encoder'],['auto','cpu','nvenc','qsv','amf']);self.combo(config,'Định dạng tự động',self.vars['export_format'],['mp4','mkv']);self.entry(config,'Tên video tự động',self.vars['auto_filename'])
        ttk.Label(config,text='720: ngang 1280×720 / dọc 720×1280. 1080: ngang 1920×1080 / dọc 1080×1920. fill cắt kín khung; contain giữ toàn cảnh và thêm viền đen. Không kéo méo hình.',wraplength=370).pack(anchor='w',pady=6)
        self.combo(config,'Chế độ tốc độ',self.vars['quality'],['fast','balanced','quality']);self.combo(config,'Whisper',self.vars['whisper_model'],['tiny','base','small']);self.combo(config,'Ngôn ngữ voice',self.vars['language'],[f'{code} | {name}' for code,name in LABELS.items()]);self.combo(config,'CPU nhận dạng',self.vars['threads'],['1','2','4','8']);self.combo(config,'Khung hình',self.vars['fit'],['fill','contain'])
        ttk.Label(config,text='auto nhận diện ngôn ngữ. Lời ngoại ngữ được dịch theo mốc sang Anh để chọn hình; giữ nguyên voice/phụ đề gốc. Có thể cung cấp Tham chiếu Anh. H’Mông cần SRT tham chiếu đúng mốc. Cảnh nền vàng cần xem lại.',wraplength=370).pack(anchor='w',pady=6)
        for k,t in [('auto_effects','Tự tạo chuyển động cho ảnh'),('auto_transitions','Tự chọn chuyển cảnh nhẹ'),('screen_minors','Lọc trẻ em ước lượng bằng AI'),('full_verify','Kiểm tra giải mã toàn phim sau xuất')]:ttk.Checkbutton(config,text=t,variable=self.vars[k]).pack(anchor='w',pady=4)
        ttk.Label(config,text='fast: 1 mẫu/cảnh + Whisper nhanh. balanced/quality: 3 mẫu/cảnh. Có SRT đúng mốc thì bỏ qua Whisper. Cache AI dùng lại giữa dự án. Các tùy chọn AI áp dụng khi Tự xếp cảnh lại.',wraplength=370).pack(anchor='w',pady=10)
        self.button(config,'Áp dụng cài đặt',self.apply_settings).pack(fill='x')
        foot=ttk.Frame(self);foot.pack(fill='x',padx=10,pady=4);self.progress=ttk.Progressbar(foot,maximum=100);self.progress.pack(fill='x');ttk.Label(foot,textvariable=self.status,wraplength=1300).pack(anchor='w');self.log=tk.Text(self,height=3,wrap='word');self.log.pack(fill='x',padx=10,pady=(0,6))
    def safe(self,fn):
        try:
            if self.busy:raise ValueError('Đang xử lý. Chờ xong hoặc bấm Dừng tác vụ trước khi sửa.')
            fn()
        except Exception as e:messagebox.showerror('AutoDoc Studio',str(e))
    def settings(self):
        d={k:v.get() for k,v in self.vars.items()};d.update(subtitle_path=self.subpath.get().strip(),visual_script_path=self.visualpath.get().strip(),subtitle_style={k:v.get() for k,v in self.stylevars.items()});d['language']=d['language'].split(' | ')[0]
        for k in ['resolution','fps','threads']:d[k]=int(d[k])
        for k in ['logo_size','logo_opacity','source_volume']:d[k]=float(d[k])
        return options(d)
    def restore_settings(self):
        d=self.p['settings']
        for k,var in self.vars.items():var.set(d[k])
        for k,var in self.stylevars.items():var.set(d['subtitle_style'][k])
        self.subpath.set(d.get('subtitle_path',''))
        self.visualpath.set(d.get('visual_script_path',''))
    def worker(self,fn,callback):
        self.player.stop();self.busy=True;self.cancel.clear();ctx=Context(lambda pct,msg:self.queue.put(('progress',pct,msg)),self.cancel)
        def task():
            try:self.queue.put(('done',callback,fn(ctx)))
            except Cancelled as e:self.queue.put(('cancelled',None,str(e)))
            except Exception as e:
                (data_dir()/'last_error.log').write_text(traceback.format_exc(),encoding='utf-8');self.queue.put(('error',None,str(e)))
        threading.Thread(target=task,daemon=True).start()
    def poll(self):
        try:
            while True:
                kind,a,b=self.queue.get_nowait()
                if kind=='progress':self.progress['value']=a;self.status.set(b);self.log.insert('end',b+'\n');self.log.see('end')
                elif kind=='done':
                    self.busy=False
                    try:a(b)
                    except Exception as e:messagebox.showerror('AutoDoc Studio',str(e))
                else:
                    self.busy=False;self.status.set(b)
                    if kind=='error':messagebox.showerror('AutoDoc Studio',b)
        except queue.Empty:pass
        self.after(70,self.poll)
    def analyze(self):
        from .pipeline import prepare
        voice,media,out=self.voice.get().strip(),self.media.get().strip(),self.output.get().strip();settings=self.settings()
        if self.p and not messagebox.askyesno('Xếp lại cảnh','Tạo bản xếp cảnh mới? Hãy lưu các chỉnh sửa muốn giữ trước.'):return
        self.worker(lambda ctx:prepare(voice,media,out,settings,ctx),self.accept_project)
    def auto_edit(self):
        from .pipeline import automatic
        voice,media,out=self.voice.get().strip(),self.media.get().strip(),self.output.get().strip();settings=self.settings()
        if not voice or not media or not out:raise ValueError('Chọn voice, thư mục ảnh/video và nơi lưu trước.')
        # Preserve the current editable project before a separate automatic job.
        if self.p:
            import time
            snapshot=copy.deepcopy(self.p);history=Path(snapshot['job'])/'history'/f'before_auto_{time.time_ns()}.json';save(snapshot,history)
        self.last_auto_result=None
        self.worker(lambda ctx:automatic(voice,media,out,settings,ctx),self.auto_finished)
    def auto_finished(self,result):
        self.last_auto_result=result;self.accept_project(load(result['project']));self.exported(result)
    def accept_project(self,p):
        self.p=p;self.selected=0;self.restore_settings();self.voice.set(p['voice_source']);self.media.set(p['media_folder']);self.refresh();low=sum(s.get('semantic_score',0)<.19 for s in p['plan']['shots']);language=LABELS.get(p.get('detected_language'),p.get('detected_language',''));self.status.set(f'Đã xếp {len(p["plan"]["shots"])} cảnh. Ngôn ngữ: {language}. {low} cảnh nền vàng cần xem lại.');self.select_index(0)
    def require(self):
        if not self.p:raise ValueError('Hãy Tự xếp cảnh hoặc Mở dự án trước.')
    def refresh(self):
        self.timeline.delete(*self.timeline.get_children());fps=self.p['plan']['fps']
        for i,s in enumerate(self.p['plan']['shots']):self.timeline.insert('', 'end',iid=str(i),values=(f'{s["start_frame"]/fps:.2f}–{s["end_frame"]/fps:.2f}',s['source_name'],NAMES.get(s.get('effect','none'),s.get('effect')),s.get('semantic_score','')),tags=('review',) if s.get('semantic_score',0)<.19 else ())
        self.sourcebox['values']=[f'{f["id"]} | {f["name"]}' for f in self.p['files']];self.refresh_cues()
    def select_index(self,i):
        self.timeline.selection_set(str(i));self.timeline.see(str(i))
    def select_scene(self,event=None):
        if not self.p or self.busy or not self.timeline.selection():return
        self.selected=int(self.timeline.selection()[0]);s=self.p['plan']['shots'][self.selected]
        for k,v in self.edit.items():
            value=s.get(k,'none' if k=='effect' else 'cut' if k=='transition' else 0)
            if k=='source_id':value=f'{value} | {self.p["files"][value]["name"]}'
            elif k=='effect':value=f'{value} | {NAMES.get(value,value)}'
            elif k=='transition':value=f'{value} | {TRANSITION_NAMES[value]}'
            v.set(value)
        self.scene_text.delete('1.0','end');self.scene_text.insert('1.0',s.get('text',''));self.request_preview()
    def request_preview(self):
        if self.preview_pending:self.after_cancel(self.preview_pending)
        self.preview_pending=self.after(220,self.preview)
    def preview(self):
        self.preview_pending=None
        if self.busy or not self.p:return
        p=copy.deepcopy(self.p);i=self.selected
        self.worker(lambda ctx:scene_preview(p,i,ctx),lambda result:(self.player.load(*result),self.status.set(f'Xem trước cảnh {i+1}. Bấm Phát để nghe đoạn voice tương ứng.')))
    def apply_scene(self):
        self.require();s=self.p['plan']['shots'][self.selected];new=copy.deepcopy(s)
        for k,var in self.edit.items():new[k]=int(var.get().split(' | ')[0]) if k=='source_id' else var.get().split(' | ')[0] if k in ['effect','transition'] else float(var.get())
        new['source_name']=self.p['files'][new['source_id']]['name'];self.p['plan']['shots'][self.selected]=new
        try:from .project import validate_project;validate_project(self.p)
        except Exception:self.p['plan']['shots'][self.selected]=s;raise
        self.refresh();self.select_index(self.selected)
    def apply_settings(self):
        settings=self.settings()
        if self.p:self.p['settings']=settings;self.request_preview()
        else:self.status.set('Đã chọn cài đặt. Bấm TỰ ĐỘNG EDIT & XUẤT để bắt đầu.')
    def set_focus(self,x,y):
        if self.busy or not self.p:return
        self.edit['focus_x'].set(f'{x:.3f}');self.edit['focus_y'].set(f'{y:.3f}');self.safe(self.apply_scene)
    def move(self,delta):
        self.require();i=self.selected;swap_sources(self.p,i,i+delta);self.refresh();self.select_index(i)
    def split_scene(self):
        self.require();split(self.p,self.selected,self.player.position);self.refresh();self.select_index(self.selected)
    def merge_scene(self):
        self.require();merge_previous(self.p,self.selected);self.selected=max(0,self.selected-1);self.refresh();self.select_index(self.selected)
    def open_project(self):
        path=filedialog.askopenfilename(filetypes=[('Dự án AutoDoc','*.json')])
        if path:self.accept_project(load(path))
    def save_project(self):
        self.require();self.p['settings']=self.settings();path=filedialog.asksaveasfilename(defaultextension='.json',initialfile=Path(self.p['project_file']).name,filetypes=[('Dự án AutoDoc','*.json')])
        if path:save(self.p,path);self.status.set('Đã lưu dự án: '+path)
    def refresh_cues(self):
        self.cuetree.delete(*self.cuetree.get_children())
        for i,c in enumerate(self.p['cues']):self.cuetree.insert('','end',iid=str(i),values=(f'{c["start"]:.2f}–{c["end"]:.2f}',c['text'][:160]))
    def select_cue(self,event=None):
        if not self.p or not self.cuetree.selection():return
        c=self.p['cues'][int(self.cuetree.selection()[0])]
        for k,v in self.cuevars.items():v.set(c[k])
        self.cuetext.delete('1.0','end');self.cuetext.insert('1.0',c['text'])
    def apply_cue(self):
        self.require()
        if not self.cuetree.selection():raise ValueError('Chọn một câu phụ đề.')
        index=int(self.cuetree.selection()[0]);c={k:seconds(v.get()) for k,v in self.cuevars.items()};c['text']=self.cuetext.get('1.0','end').strip();new=copy.deepcopy(self.p['cues']);new[index]=c;self.p['cues']=validate(new,self.p['plan']['voice_seconds']);self.refresh_cues();self.request_preview()
    def add_cue(self):
        self.require();start=self.p['plan']['shots'][self.selected]['start_frame']/self.p['plan']['fps'];self.p['cues']=validate(self.p['cues']+[{'start':start,'end':min(start+2,self.p['plan']['voice_seconds']),'text':'New subtitle'}],self.p['plan']['voice_seconds']);self.refresh_cues()
    def delete_cue(self):
        self.require()
        if not self.cuetree.selection():return
        if len(self.p['cues'])<=1:raise ValueError('Giữ ít nhất một câu lời để xếp cảnh.')
        del self.p['cues'][int(self.cuetree.selection()[0])];self.refresh_cues();self.request_preview()
    def import_subs(self):
        self.require();path=filedialog.askopenfilename(filetypes=[('TXT/SRT','*.txt *.srt')])
        if not path:return
        if Path(path).suffix.lower()=='.srt':self.p['cues']=read_srt(path,self.p['plan']['voice_seconds'])
        else:
            cues,ratio=align_txt(read_txt(path),self.p['cues'],self.p['plan']['voice_seconds']);self.p['cues']=cues;self.status.set(f'TXT căn theo lời hiện tại: khớp {ratio:.0%}. Kiểm tra lại các mốc.')
        self.subpath.set(path);self.p['settings']['subtitle_path']=path;self.refresh_cues();self.request_preview()
    def export_subs(self):
        self.require();path=filedialog.asksaveasfilename(defaultextension='.srt',filetypes=[('SRT có mốc','*.srt'),('TXT lời','*.txt')])
        if path:
            if Path(path).resolve() in {Path(f['path']).resolve() for f in self.p['files']}|{Path(self.p['voice_source']).resolve()}:raise ValueError('Không ghi đè nguồn.')
            export(self.p['cues'],path);self.status.set('Đã xuất phụ đề: '+path)
    def pick_color(self,key):
        value=colorchooser.askcolor(self.stylevars[key].get())[1]
        if value:self.stylevars[key].set(value)
    def refresh_effects(self):self.effectbox['values']=[f'{k} | {NAMES.get(k,k)}' for k in installed_effects()]
    def get_pack(self):self.worker(lambda ctx:install_pack(ctx),lambda result:(self.refresh_effects(),self.status.set('Đã cài gói hiệu ứng bổ sung; chọn tại tab Cảnh.')))
    def export_dialog(self):
        self.require();self.p['settings']=self.settings();win=tk.Toplevel(self);win.title('Xuất video');win.transient(self);win.grab_set();win.geometry('530x460')
        for k,label,values in [('aspect_ratio','Tỷ lệ video',['16:9','9:16']),('resolution','Độ nét (cạnh ngắn)',[720,1080]),('fps','Khung/giây',[24,25,30,60]),('quality','Tốc độ / chất lượng',['fast','balanced','quality']),('encoder','Bộ mã hóa',['auto','cpu','nvenc','qsv','amf'])]:self.combo(win,label,self.vars[k],values)
        ttk.Checkbutton(win,text='Giải mã kiểm tra toàn bộ phim (tốn thêm thời gian)',variable=self.vars['full_verify']).pack(anchor='w',padx=15,pady=10)
        ttk.Label(win,text='auto: thử GPU thực tế, quay về CPU nếu không hỗ trợ.\nMP4 tương thích rộng; MKV hỗ trợ phụ đề mềm.\nKiểu màu/phông dùng chế độ burn. Mọi bản đều lưu vào đường dẫn bạn chọn.',wraplength=470).pack(padx=15,pady=10)
        def begin():
            try:
                settings=self.settings();path=filedialog.asksaveasfilename(defaultextension='.mp4',initialdir=self.p['job'],initialfile='VIDEO_HOAN_CHINH.mp4',filetypes=[('MP4','*.mp4'),('MKV','*.mkv')],parent=win)
                if not path:return
                self.p['settings']=settings;save(self.p);p=copy.deepcopy(self.p);win.destroy()
                from .render import export_movie
                self.worker(lambda ctx:export_movie(p,path,ctx),self.exported)
            except Exception as e:messagebox.showerror('Xuất video',str(e),parent=win)
        ttk.Button(win,text='Chọn nơi lưu và xuất',command=begin).pack(fill='x',padx=20,pady=5);ttk.Button(win,text='Hủy',command=win.destroy).pack(pady=4)
    def exported(self,r):self.last_export=r['output'];self.status.set('Đã lưu video: '+self.last_export);self.request_preview();messagebox.showinfo('Hoàn tất','Video đã lưu:\n'+self.last_export)
    def open_result(self):
        if not self.last_export or not Path(self.last_export).is_file():raise ValueError('Chưa có video xuất trong phiên này.')
        if os.name=='nt':os.startfile(self.last_export)
        else:__import__('subprocess').Popen(['xdg-open',self.last_export])
    def close(self):
        if self.busy and not messagebox.askyesno('Đang xử lý','Dừng tác vụ và đóng tool? Cache đã xong sẽ được giữ.'):return
        self.cancel.set();self.player.cleanup();save_json(self.preferences,{'output':self.output.get(),'last_project':self.p['project_file'] if self.p else ''})
        def finish():
            if self.busy:self.after(150,finish)
            else:self.destroy()
        self.status.set('Đang dừng tiến trình trước khi đóng…');finish()

def main():App().mainloop()
