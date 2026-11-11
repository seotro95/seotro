from __future__ import annotations
import json,os,queue,subprocess,sys,threading,traceback
from pathlib import Path
import tkinter as tk
from tkinter import filedialog,messagebox,ttk
from .common import Cancelled,Context,data_dir
from .pipeline import Settings,run

class App(tk.Tk):
    def __init__(self):
        super().__init__();self.title('AutoDoc Studio1.0 — Tự dựng theo voice');self.geometry('960x720');self.minsize(790,630)
        self.configure(bg='#111827');self.events=queue.Queue();self.stop=threading.Event();self.worker=None;self.result=None
        self.vars={k:tk.StringVar(value=v) for k,v in {'voice':'','videos':'','output':str(Path.home()/'Videos'/'AutoDoc_Output'),'resolution':'720p — nhanh,nhẹ','language':'English','model':'base'}.items()}
        self.subs=tk.BooleanVar(value=False);self.minors=tk.BooleanVar(value=True)
        style=ttk.Style(self);style.theme_use('clam');style.configure('TFrame',background='#111827');style.configure('TLabel',background='#111827',foreground='#e5e7eb',font=('Segoe UI',10));style.configure('TButton',font=('Segoe UI',10),padding=(12,8));style.configure('TCheckbutton',background='#111827',foreground='#e5e7eb',font=('Segoe UI',10));style.map('TCheckbutton',background=[('active','#1f2937')]);style.configure('Accent.TButton',background='#38bdf8',foreground='#082f49',font=('Segoe UI',11,'bold'));style.configure('TProgressbar',background='#38bdf8',troughcolor='#263244',bordercolor='#263244')
        main=ttk.Frame(self,padding=24);main.pack(fill='both',expand=True)
        tk.Label(main,text='AUTODOC STUDIO',bg='#111827',fg='#7dd3fc',font=('Segoe UI',10,'bold')).pack(anchor='w')
        tk.Label(main,text='Voice + video → Phim hoàn chỉnh',bg='#111827',fg='white',font=('Segoe UI',23,'bold')).pack(anchor='w',pady=(5,6))
        ttk.Label(main,text='Tự đọc lời • AI chọn cảnh •10cảnh/30giây đầu • Chỉ tiếng từ voice',wraplength=850).pack(anchor='w',pady=(0,20))
        for key,label,kind in [('voice','1. Chọn voice','file'),('videos','2. Thư mục video','folder'),('output','3. Nơi lưu kết quả','folder')]:
            row=ttk.Frame(main);row.pack(fill='x',pady=5);ttk.Label(row,text=label,width=23).pack(side='left')
            entry=ttk.Entry(row,textvariable=self.vars[key]);entry.pack(side='left',fill='x',expand=True,padx=(0,8))
            ttk.Button(row,text='Chọn…',command=lambda k=key,t=kind:self.browse(k,t)).pack(side='right')
        options=ttk.Frame(main);options.pack(fill='x',pady=(16,8))
        ttk.Label(options,text='Chất lượng').pack(side='left');ttk.Combobox(options,textvariable=self.vars['resolution'],values=['720p — nhanh,nhẹ','1080p — rõ hơn'],state='readonly',width=22).pack(side='left',padx=(8,20))
        ttk.Label(options,text='Lời đọc').pack(side='left');ttk.Combobox(options,textvariable=self.vars['language'],values=['English','Tự nhận ngôn ngữ'],state='readonly',width=20).pack(side='left',padx=8)
        ttk.Checkbutton(main,text='Kèm phụ đề tùy chọn trong MP4 (không đốt chữ lên hình)',variable=self.subs).pack(anchor='w',pady=4)
        ttk.Checkbutton(main,text='Hạn chế cảnh có trẻ em bằng AI (ước lượng,không bảo đảm tuyệt đối)',variable=self.minors).pack(anchor='w',pady=4)
        buttons=ttk.Frame(main);buttons.pack(fill='x',pady=(16,12))
        self.start_button=ttk.Button(buttons,text='TỰ DỰNG VIDEO',style='Accent.TButton',command=self.start);self.start_button.pack(side='left')
        self.cancel_button=ttk.Button(buttons,text='Dừng',command=self.cancel,state='disabled');self.cancel_button.pack(side='left',padx=8)
        self.open_button=ttk.Button(buttons,text='Mở kết quả',command=self.open_result,state='disabled');self.open_button.pack(side='right')
        self.progress=ttk.Progressbar(main,maximum=100);self.progress.pack(fill='x',pady=(0,6));self.status=ttk.Label(main,text='Sẵn sàng. Lần đầu cần mạng để tải model;không cần APItrả phí.',wraplength=850);self.status.pack(anchor='w')
        self.log=tk.Text(main,height=9,bg='#0b1220',fg='#cbd5e1',insertbackground='white',relief='flat',font=('Consolas',9),state='disabled');self.log.pack(fill='both',expand=True,pady=(12,8))
        ttk.Label(main,text='Nguồn được giữ nguyên. Cảnh thiếu dùng video liên quan,không tạo ảnh/bảng chữ để bù.\nAI xếp cảnh theo tương đồng;hãy xem bản dựng trước khi đăng.',wraplength=850).pack(anchor='w')
        self.load_preferences();self.after(100,self.poll);self.protocol('WM_DELETE_WINDOW',self.close)

    def browse(self,key,kind):
        if self.worker and self.worker.is_alive():return
        value=filedialog.askopenfilename(title='Chọn tệp voice',filetypes=[('Audio','*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus *.wma'),('Tất cả','*.*')]) if kind=='file' else filedialog.askdirectory(title='Chọn thư mục')
        if value:self.vars[key].set(value)

    def load_preferences(self):
        p=data_dir()/'preferences.json'
        if p.exists():
            try:
                d=json.loads(p.read_text())
                for k,v in d.items():
                    if k in self.vars:self.vars[k].set(v)
            except (OSError,ValueError):pass

    def start(self):
        if self.worker and self.worker.is_alive():return
        settings=Settings(voice=self.vars['voice'].get(),videos=self.vars['videos'].get(),output=self.vars['output'].get(),resolution=1080 if self.vars['resolution'].get().startswith('1080') else 720,language='en' if self.vars['language'].get()=='English' else 'auto',embed_subtitles=self.subs.get(),screen_minors=self.minors.get())
        if not settings.voice or not settings.videos or not settings.output:messagebox.showwarning('Thiếu đầu vào','Chọn voice,thư mục video và nơi lưu kết quả.');return
        (data_dir()/'preferences.json').write_text(json.dumps({k:v.get() for k,v in self.vars.items()},ensure_ascii=False),encoding='utf-8')
        self.stop.clear();self.result=None;self.start_button.configure(state='disabled');self.cancel_button.configure(state='normal');self.open_button.configure(state='disabled');self.progress['value']=0
        def task():
            try:
                result=run(settings,Context(lambda pct,msg:self.events.put(('progress',pct,msg)),self.stop));self.events.put(('done',result))
            except Cancelled as e:self.events.put(('cancelled',str(e)))
            except Exception as e:
                details=traceback.format_exc();(data_dir()/'last_error.log').write_text(details,encoding='utf-8');self.events.put(('error',str(e)))
        self.worker=threading.Thread(target=task,daemon=True);self.worker.start()

    def poll(self):
        try:
            while True:
                event=self.events.get_nowait();kind=event[0]
                if kind=='progress':
                    self.progress['value']=max(float(self.progress['value']),event[1]);self.status.configure(text=event[2]);self.add_log(event[2])
                else:
                    self.start_button.configure(state='normal');self.cancel_button.configure(state='disabled')
                    if kind=='done':
                        self.result=event[1];self.open_button.configure(state='normal');self.status.configure(text='Hoàn tất — '+self.result['output']);self.add_log('Đã kiểm tra file xuất. '+str(len(self.result['report']['warnings']))+'ghi chú trong KIEM_TRA_VIDEO.json.');messagebox.showinfo('Đã dựng xong','Video đã xuất và kiểm tra.\n\n'+self.result['output']+'\n\nXem bản dựng trước khi đăng.')
                    elif kind=='cancelled':self.status.configure(text=event[1]);self.add_log(event[1])
                    else:self.status.configure(text='Chưa hoàn tất. Xem lỗi bên dưới.');self.add_log(event[1]);messagebox.showerror('Không hoàn tất',event[1])
        except queue.Empty:pass
        self.after(100,self.poll)

    def add_log(self,text):
        self.log.configure(state='normal');self.log.insert('end',text+'\n');self.log.see('end');self.log.configure(state='disabled')

    def cancel(self):self.stop.set();self.status.configure(text='Đang dừng an toàn… tải model/nhận dạng có thể cần kết thúc khối hiện tại.')
    def open_result(self):
        if not self.result:return
        p=self.result['project']
        if os.name=='nt':os.startfile(p)
        elif sys.platform=='darwin':subprocess.Popen(['open',p])
        else:subprocess.Popen(['xdg-open',p])
    def close(self):
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno('Đang dựng','Dừng và đóng ứng dụng? Cache sẽ được giữ.'):return
            self.stop.set();self.after(300,self.destroy)
        else:self.destroy()

def main():App().mainloop()
