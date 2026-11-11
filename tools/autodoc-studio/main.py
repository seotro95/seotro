from __future__ import annotations
import argparse,json,sys,os
from pathlib import Path
if getattr(sys,'frozen',False) and sys.stdout is None:
    logdir=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'AutoDocStudio';logdir.mkdir(parents=True,exist_ok=True)
    sys.stdout=sys.stderr=(logdir/'application.log').open('a',encoding='utf-8',buffering=1)

def main():
    parser=argparse.ArgumentParser(description='AutoDoc Studio 2 — local voice/image/video editor')
    for name in ['voice','videos','media','output','project','export-to','settings','result-json','doctor-output','gui-report','gui-qa-config']:parser.add_argument('--'+name)
    parser.add_argument('--prepare-only',action='store_true');parser.add_argument('--auto-edit',action='store_true',help='Tự xếp cảnh và xuất hoàn chỉnh.');parser.add_argument('--doctor',action='store_true');parser.add_argument('--gui-smoke',action='store_true')
    args=parser.parse_args()
    try:
        if args.gui_qa_config:
            from autodoc.qa import run
            run(args.gui_qa_config,args.gui_report);return
        if args.doctor:
            from autodoc.resources import check_vad
            vad_status=check_vad()
            from autodoc.bootstrap import ensure_ffmpeg
            from autodoc.common import Context,binary
            ensure_ffmpeg(Context(lambda *_:None));import av,ctranslate2,faster_whisper,numpy,onnxruntime,tokenizers,tkinter,langid
            result={'status':'ready','version':'2.2.1','ffmpeg':binary('ffmpeg'),'ffprobe':binary('ffprobe'),'tk_version':tkinter.TkVersion,'onnx':onnxruntime.__version__,'vad':vad_status}
            if args.doctor_output:Path(args.doctor_output).write_text(json.dumps(result),encoding='utf-8')
        elif args.gui_smoke:
            from autodoc.gui import App
            app=App();result={'status':'started'};ticks=[0]
            if args.project:
                from autodoc.project import load
                app.accept_project(load(args.project))
            def finish():
                ticks[0]+=1
                if (app.busy or app.preview_pending or (args.project and app.player._photo is None)) and ticks[0]<100:app.after(200,finish);return
                payload={'status':'passed','widgets':len(app.winfo_children()),'project_loaded':bool(app.p),'preview_loaded':bool(app.player.path),'preview_frame_displayed':app.player._photo is not None,'scene_count':len(app.p['plan']['shots']) if app.p else 0}
                if args.project and (not app.player.path or app.player._photo is None):payload['status']='failed'
                if args.gui_report:Path(args.gui_report).write_text(json.dumps(payload),encoding='utf-8')
                app.player.cleanup();app.destroy()
            app.after(1000,finish);app.mainloop();return
        elif args.voice or args.media or args.videos:
            if not args.voice or not (args.media or args.videos) or not args.output:parser.error('Cần --voice, --media và --output.')
            from autodoc.pipeline import run
            settings=json.loads(Path(args.settings).read_text(encoding='utf-8-sig')) if args.settings else None
            result=run(args.voice,args.media or args.videos,args.output,settings,prepare_only=args.prepare_only)
        elif args.project:
            from autodoc.project import load
            from autodoc.render import export_movie
            from autodoc.common import Context
            p=load(args.project)
            if args.settings:
                from autodoc.project import options
                p['settings']=options({**p['settings'],**json.loads(Path(args.settings).read_text(encoding='utf-8-sig'))})
            result=export_movie(p,args.export_to or str(Path(p['job'])/'VIDEO_HOAN_CHINH.mp4'),Context())
        else:
            from autodoc.gui import main as gui
            gui();return
        if args.result_json:Path(args.result_json).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False))
    except Exception as e:
        import traceback
        traceback.print_exc()
        if args.result_json:Path(args.result_json).write_text(json.dumps({'status':'failed','error':str(e)},ensure_ascii=False),encoding='utf-8')
        raise SystemExit(1)

if __name__=='__main__':main()
