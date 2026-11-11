"""Explicitly invoked acceptance driver for the frozen Windows UI, no media bundled."""
from __future__ import annotations
import json,time
from pathlib import Path
from .common import save_json,digest
from .project import load

def run(config_path,report_path):
    from . import gui
    cfg=json.loads(Path(config_path).read_text(encoding='utf-8-sig'));app=gui.App();checks={};errors=[];work=Path(cfg['work']);work.mkdir(parents=True,exist_ok=True)
    gui.messagebox.showerror=lambda title,text,**kwargs:errors.append(str(text))
    gui.messagebox.showinfo=lambda *a,**k:None
    gui.messagebox.askyesno=lambda *a,**k:True
    pending=[None];started=[0.];label=[''];report=Path(report_path)
    def ready():return not app.busy and app.preview_pending is None
    def frame_ready():return ready() and app.player._photo is not None
    def wait(predicate,name,timeout=180):return predicate,name,timeout
    def fields(d):
        for k,v in d.items():app.vars[k].set(v)
    def steps():
        app.accept_project(load(cfg['project']))
        yield wait(frame_ready,'open project and display decoded frame')
        checks['open_project_and_preview_frame']=True
        total=app.p['plan']['total_frames'];app.edit['source_in'].set('.2');app.edit['crop'].set('1.1');app.edit['speed'].set('1.25');app.edit['effect'].set('warm | Ấm');app.edit['transition'].set('wipeleft | Lau trái');app.apply_scene()
        yield wait(frame_ready,'edit source, crop, speed, effect, transition')
        s=app.p['plan']['shots'][0];assert s['speed']==1.25 and s['crop']==1.1 and s['effect']=='warm' and s['transition']=='wipeleft';checks['scene_edit_controls']=True
        app.set_focus(.6,.4)
        yield wait(frame_ready,'crop focus')
        assert app.p['plan']['shots'][0]['focus_x']==.6;checks['click_crop_focus']=True
        app.player.toggle();start=time.monotonic()
        yield wait(lambda:time.monotonic()-start>.65,'play preview',10)
        assert app.player.position>.15;app.player.stop();app.player.seek(.8);checks['play_pause_seek_preview']=True
        count=len(app.p['plan']['shots']);app.split_scene()
        yield wait(frame_ready,'split scene')
        assert len(app.p['plan']['shots'])==count+1 and app.p['plan']['total_frames']==total
        app.select_index(1)
        yield wait(frame_ready,'select second scene')
        app.merge_scene()
        yield wait(frame_ready,'merge scene')
        assert len(app.p['plan']['shots'])==count and app.p['plan']['total_frames']==total;checks['split_merge_preserves_voice_duration']=True
        a=app.p['plan']['shots'][0]['source_id'];b=app.p['plan']['shots'][1]['source_id'];app.move(1)
        yield wait(frame_ready,'move source')
        assert app.p['plan']['shots'][0]['source_id']==b and app.p['plan']['shots'][1]['source_id']==a;checks['move_source_controls']=True
        app.cuetree.selection_set('0');app.select_cue();app.cuevars['start'].set(0);app.cuevars['end'].set(1.5);app.cuetext.delete('1.0','end');app.cuetext.insert('1.0','Voice-led story.');app.apply_cue()
        yield wait(ready,'edit subtitle')
        assert app.p['cues'][0]['text']=='Voice-led story.';n=len(app.p['cues']);app.add_cue();new=next(i for i,c in enumerate(app.p['cues']) if c['text']=='New subtitle');app.cuetree.selection_set(str(new));app.delete_cue()
        yield wait(ready,'add delete subtitle')
        assert len(app.p['cues'])==n;checks['subtitle_edit_add_delete']=True
        for ext in ['srt','txt']:
            path=work/f'exported_subtitles.{ext}';gui.filedialog.asksaveasfilename=lambda **kwargs:str(path);app.export_subs();assert 'Voice-led story.' in path.read_text(encoding='utf-8-sig')
            gui.filedialog.askopenfilename=lambda **kwargs:str(path);app.import_subs()
            yield wait(ready,'import export '+ext)
        checks['import_export_txt_and_srt']=True
        gui.colorchooser.askcolor=lambda *a,**k:((255,204,0),'#FFCC00');app.pick_color('color');assert app.stylevars['color'].get()=='#FFCC00'
        for k,v in {'font':'Arial','size':36,'outline':3,'bold':True,'italic':True,'position':'top','background':True}.items():app.stylevars[k].set(v)
        fields({'logo_path':cfg['logo'],'logo_position':'bottom_right','logo_size':15,'logo_opacity':.65,'mute_source':False,'source_volume':.25,'subtitle_mode':'burn'});app.apply_settings()
        yield wait(frame_ready,'logo and subtitle appearance')
        assert app.p['settings']['subtitle_style']['italic'] and app.p['settings']['logo_opacity']==.65 and not app.p['settings']['mute_source'];checks['logo_audio_and_subtitle_style_controls']=True
        saved=work/'gui saved project.json';gui.filedialog.asksaveasfilename=lambda **kwargs:str(saved);app.save_project();gui.filedialog.askopenfilename=lambda **kwargs:str(saved);app.open_project()
        yield wait(frame_ready,'save reopen project')
        assert app.p['settings']['subtitle_style']['color']=='#FFCC00' and app.p['plan']['total_frames']==total;checks['save_and_reopen_project']=True
        app.get_pack()
        yield wait(ready,'download effect pack')
        assert len(app.effectbox['values'])==20;checks['download_install_effect_pack']=True
        fields({'resolution':1080,'fps':25,'quality':'fast','encoder':'cpu','full_verify':True});manual=work/'GUI manual export.mp4';gui.filedialog.asksaveasfilename=lambda **kwargs:str(manual);app.export_dialog()
        windows=[x for x in app.winfo_children() if isinstance(x,gui.tk.Toplevel)];win=windows[-1];next(x for x in win.winfo_children() if isinstance(x,gui.ttk.Button) and x.cget('text')=='Chọn nơi lưu và xuất').invoke()
        yield wait(lambda:ready() and app.last_export==str(manual.resolve()),'manual export dialog',240)
        q=json.loads(manual.with_suffix('.qa.json').read_text(encoding='utf-8-sig'));assert q['width']==1920 and q['fps']==25 and q['source_audio_kept'];checks['manual_export_dialog_1080p_25fps']=True
        opened=[];gui.os.startfile=lambda path:opened.append(path);app.open_result();assert opened==[app.last_export];checks['open_exported_video_action']=True
        # Invoke the same visible button a user clicks, with no subtitle file.
        app.voice.set(cfg['auto_voice']);app.media.set(cfg['media']);app.output.set(cfg['auto_output']);app.subpath.set('')
        fields({'aspect_ratio':'9:16','resolution':720,'fps':24,'quality':'fast','encoder':'auto','whisper_model':'tiny','logo_path':'','mute_source':True,'subtitle_mode':'none','full_verify':True,'screen_minors':False,'auto_filename':'AUTO_GUI_Đã dựng','export_format':'mp4'})
        app.auto_button.invoke()
        yield wait(lambda:ready() and app.last_auto_result is not None,'automatic GUI edit with actual ASR',300)
        result=app.last_auto_result;movie=Path(result['output']);assert movie.is_file() and result['workflow']=='automatic' and not result['asr_skipped'];p=load(result['project']);assert p['plan']['opening_shots']==10 and p['plan']['opening_seconds']==30 and p['plan']['opening_distinct_files']==10
        assert result['report']['audio_alignment'] and not result['report']['source_audio_kept'];assert result['report']['width']==720 and result['report']['height']==1280 and p['settings']['aspect_ratio']=='9:16';checks['one_click_automatic_gui_without_subtitles']=True;checks['automatic_ten_scene_30_second_opening']=True;checks['automatic_video_and_reopenable_project_saved']=True;checks['automatic_portrait_9_16_720x1280']=True
        sha=digest(movie);app.auto_button.invoke();app.cancel.set()
        yield wait(ready,'cancel automatic edit',60)
        assert app.last_auto_result is None and digest(movie)==sha;checks['cancel_keeps_completed_video']=True
        app.auto_button.invoke()
        yield wait(lambda:ready() and app.last_auto_result is not None,'resume automatic workflow',300)
        second=app.last_auto_result;assert second['output']!=str(movie) and digest(movie)==sha;checks['repeat_auto_keeps_previous_export']=True
        yield wait(frame_ready,'preview automatically generated project')
        assert app.player.video_height>app.player.video_width;checks['portrait_preview_orientation_correct']=True
        checks['automatic_result_editable_in_gui']=True
    generator=steps()
    def finish(ok,detail=None):
        payload={'status':'passed' if ok else 'failed','checks':checks,'error':detail,'frozen_gui_actions_tested':True,'tests_do_not_prove_aesthetic_or_factually_exact_AI_selection':True}
        save_json(report,payload);app.cancel.set();app.player.cleanup();app.destroy()
    def advance():
        try:
            if errors:raise RuntimeError(errors[-1])
            if pending[0]:
                predicate,name,timeout=pending[0]
                if not predicate():
                    if time.monotonic()-started[0]>timeout:raise TimeoutError('GUI QA timeout: '+name)
                    app.after(75,advance);return
            pending[0]=next(generator);started[0]=time.monotonic();app.after(75,advance)
        except StopIteration:finish(True)
        except Exception as exc:
            import traceback
            finish(False,traceback.format_exc())
    app.after(250,advance);app.mainloop()
    if json.loads(report.read_text(encoding='utf-8-sig'))['status']!='passed':raise RuntimeError('Kiểm thử giao diện chưa đạt. Xem GUI_FEATURE_REPORT.json.')
