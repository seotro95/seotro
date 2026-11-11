"""Real, publicly released narration fixtures; never included in app packages."""
import json,os,subprocess,sys,urllib.request
from pathlib import Path
from autodoc.common import Context,binary,save_json
from autodoc.project import load
from autodoc.subtitles import export
from autodoc.languages import subtitle_language

root=Path(__file__).resolve().parent;exe=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else None
work=root/('windows test' if exe else 'local test')/'Đa ngôn ngữ';work.mkdir(parents=True,exist_ok=True)
media=Path(sys.argv[2]) if len(sys.argv)>2 else root.parent/'auto-documentary-editor-v2/local test/Nguon thu nghiem/clips';ff=binary('ffmpeg');results=[];reference=work/'English reference.srt'
samples=[('vi','Viet_Nam'),('es','Tay_Ban_Nha'),('ja','Nhat_Ban'),('hmn','Hmong_Trang_Nu')]
for code,country in samples:
    full=work/f'{country}.mp3'
    if not full.exists():
        url=f'https://github.com/seotro95/seotro/releases/download/kostenki-video-19-20m15s/KOSTENKI_19_{country}.mp3'
        with urllib.request.urlopen(url,timeout=90) as response,full.open('wb') as out:
            while True:
                b=response.read(1024*1024)
                if not b:break
                out.write(b)
    voice=work/f'Giọng {country}.wav';subprocess.run([ff,'-v','error','-i',str(full),'-t','35','-vn','-ac','1','-ar','48000','-y',str(voice)],check=True)
    config={'language':'auto' if code!='hmn' else 'hmn','whisper_model':'base','resolution':720 if exe else 360,'quality':'fast','screen_minors':False,'full_verify':True,'auto_filename':country}
    if not exe:
        config['clip_model_path']=str(root.parent/'auto-documentary-editor/test-models/clip');config['whisper_model_path']='/home/agent/.cache/huggingface/hub/models--Systran--faster-whisper-base/snapshots/ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66'
    if code=='hmn':config['visual_script_path']=str(reference)
    settings=work/f'{code}.json';result=work/f'{code}_result.json';save_json(settings,config)
    cmd=([str(exe)] if exe else [sys.executable,str(root/'main.py')])+['--auto-edit','--voice',str(voice),'--media',str(media),'--output',str(work/'kết quả'),'--settings',str(settings),'--result-json',str(result)]
    subprocess.run(cmd,check=True);r=json.loads(result.read_text(encoding='utf-8-sig'));p=load(r['project']);assert r['report']['status']=='passed' and r['report']['audio_alignment'] and not r['report']['source_audio_kept'] and abs(r['report']['video_seconds']-r['report']['voice_seconds'])<=1/24+.001
    assert p['detected_language']==code,(code,p['detected_language'])
    if code!='hmn':
        assert p['visual_matching']=='translated_en';assert subtitle_language(p['visual_cues'])[0]=='en';assert subtitle_language(p['cues'])[0]==code
    else:assert p['visual_matching']=='reference_en_srt' and p['asr_skipped']
    if code=='vi':export(p['visual_cues'],reference)
    results.append({'language':code,'status':'passed','mode':p['visual_matching'],'native_caption_language':subtitle_language(p['cues'])[0],'original_audio_alignment':r['report']['audio_alignment'],'voice_seconds':r['report']['voice_seconds'],'video_seconds':r['report']['video_seconds'],'mean_semantic_score':round(sum(s['semantic_score'] for s in p['plan']['shots'])/len(p['plan']['shots']),4)})
    print('MULTILINGUAL_PASS',code,p['visual_matching'],flush=True)
report={'status':'passed','version':'2.3.0','frozen_exe_tested':bool(exe),'results':results,'automatic_language_detection_tested':['vi','es','ja'],'hmong_is_timed_english_reference_mode_not_speech_recognition':True,'original_voice_preserved':True,'english_visual_queries_and_native_subtitles_separate':True,'semantic_score_is_similarity_not_verified_factual_accuracy':True}
save_json(root/'MULTILINGUAL_TEST_REPORT.json',report)
