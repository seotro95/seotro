from __future__ import annotations
import argparse,json,sys
from pathlib import Path
import os
if getattr(sys,'frozen',False) and sys.stdout is None:
    logdir=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'AutoDocStudio'
    logdir.mkdir(parents=True,exist_ok=True)
    sys.stdout=sys.stderr=(logdir/'application.log').open('a',encoding='utf-8',buffering=1)

def main():
    parser=argparse.ArgumentParser(description='AutoDocStudio — automatic narration-driven documentary editor')
    parser.add_argument('--result-json');parser.add_argument('--voice');parser.add_argument('--videos');parser.add_argument('--output');parser.add_argument('--resolution',type=int,choices=[720,1080],default=720)
    parser.add_argument('--language',default='en');parser.add_argument('--whisper-model',default='base');parser.add_argument('--embed-subtitles',action='store_true');parser.add_argument('--allow-minors',action='store_true',help='Disable approximate minor-screening;use only when appropriate.')
    parser.add_argument('--clip-model-path');parser.add_argument('--whisper-model-path');parser.add_argument('--doctor',action='store_true');parser.add_argument('--doctor-output');parser.add_argument('--gui-smoke',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.doctor:
        from autodoc.common import binary,Context
        from autodoc.bootstrap import ensure_ffmpeg
        ensure_ffmpeg(Context(lambda *_:None))
        import av,ctranslate2,faster_whisper,numpy,onnxruntime,tokenizers,tkinter
        payload=json.dumps({'status':'ready','ffmpeg':binary('ffmpeg'),'ffprobe':binary('ffprobe'),'python':sys.version.split()[0],'onnx':onnxruntime.__version__,'ctranslate':ctranslate2.__version__,'tk_version':tkinter.TkVersion})
        if args.doctor_output:Path(args.doctor_output).write_text(payload,encoding='utf-8')
        if sys.stdout is not None:print(payload)
        return
    if args.gui_smoke:
        from autodoc.gui import App
        app=App();app.after(700,app.destroy);app.mainloop();
        if sys.stdout is not None:print('GUI_SMOKE_PASSED')
        return
    if args.voice or args.videos or args.output:
        if not all([args.voice,args.videos,args.output]):parser.error('Cần đủ --voice,--videos,--output.')
        from autodoc.pipeline import Settings,run
        from autodoc.common import Cancelled
        try:
            result=run(Settings(args.voice,args.videos,args.output,args.resolution,args.language,args.whisper_model,args.embed_subtitles,not args.allow_minors,clip_model_path=args.clip_model_path,whisper_model_path=args.whisper_model_path))
            if args.result_json:Path(args.result_json).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(result,ensure_ascii=False))
        except (Exception,KeyboardInterrupt) as e:
            if args.result_json:Path(args.result_json).write_text(json.dumps({'status':'failed','error':str(e)},ensure_ascii=False),encoding='utf-8')
            print('ERROR:',str(e),file=sys.stderr);raise SystemExit(1)
    else:
        from autodoc.gui import main as gui_main
        gui_main()

if __name__=='__main__':main()
