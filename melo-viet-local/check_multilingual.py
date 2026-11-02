"""Real offline integration: both genders in every supported language, all ten native presets."""
import argparse,json,os,time,subprocess
from pathlib import Path
from app import Reader,Studio
from local_models import ensure
from multilingual_backend import LANGUAGES,voices_for

def main(root,output):
    root=Path(root);output=Path(output);output.mkdir(parents=True,exist_ok=True);os.environ['MELO_VIET_ROOT']=str(root)
    ensure('supertonic3',False);reader=Reader(root,'piper',True)
    samples=json.loads(Path(__file__).with_name('samples.json').read_text());report={'status':'running','runtime':'Supertonic 3 INT8 CPU, five inference steps','human_listening_quality_verified':False,'results':[]}
    try:
        for code in LANGUAGES:
            for voice in [voices_for(code)[0],voices_for(code)[5]]+(voices_for(code)[1:5]+voices_for(code)[6:] if code=='EN' else []):
                t=time.perf_counter();r=reader.request({'op':'render','backend':'multi','language':code,'voice':voice['id'],'threads':4,'text':samples[code],'output':str(output/(code+'-'+voice['id'].replace(':','-')+'.wav'))})
                assert r['audio_seconds']>.2 and 0<r['peak']<=.951 and r['sample_rate']==44100
                report['results'].append({**r,'language':code,'wall_seconds':time.perf_counter()-t});print('Native multilingual WAV passed:',code,voice['id'],flush=True)
        report['status']='passed'
    except Exception:
        log=root/'logs/piper.log'
        if log.is_file():print('::error title=Multilingual synthesis::'+log.read_text(errors='replace')[-3000:].replace('%','%25').replace('\n','%0A'),flush=True)
        raise
    finally:reader.close();(output/'MULTILINGUAL-QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    studio=Studio(root,offline=True);studio.settings(1)
    try:
        j=studio.start({'engine':'local','local_provider':'multi','language':'VI','voice':'supertonic:0','text':'Xin chào bạn. Hôm nay, chúng ta cùng khám phá **một câu chuyện thú vị**. Bạn đã sẵn sàng chưa?','name':'Friendly emphasis integration','threads':4,'expressive':True,'emphasis':True,'use_cache':False,'style':'friendly','chunk_size':180})
        deadline=time.monotonic()+180
        while studio.jobs[j['id']]['status'] not in {'done','error'} and time.monotonic()<deadline:time.sleep(.1)
        j=studio.jobs[j['id']];assert j['status']=='done',j.get('error');assert j['progress']==1 and j['cache_hits']==0
        studio.exports.start(j['id'])
        while j.get('mp3_status') not in {'done','error'} and time.monotonic()<deadline:time.sleep(.1)
        assert j['mp3_status']=='done',j.get('mp3_error')
        f=root/'outputs'/j['id']/'voice.mp3';probe=json.loads(subprocess.check_output(['ffprobe','-v','quiet','-show_streams','-of','json',str(f)]));assert probe['streams'][0]['codec_name']=='mp3'
        (output/'EXPRESSIVE-MP3-QA.json').write_text(json.dumps({k:j.get(k) for k in ['status','engine','voice','progress','expressive','emphasis','audio_seconds','processing_seconds','cache_hits','mp3_status','mp3_progress','mp3_encoding_seconds']},ensure_ascii=False,indent=2))
    finally:studio.close()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);a=p.parse_args();main(a.root,a.output)
