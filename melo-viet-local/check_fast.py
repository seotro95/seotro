"""Download only published FP32 models, then synthesize each model without network."""
import argparse
import json
import os
from pathlib import Path
import time
from app import Reader,Studio
import fast_backend


def main(root,output,prepare_only=False,threads=4):
    root=Path(root);output=Path(output);root.mkdir(parents=True,exist_ok=True);output.mkdir(parents=True,exist_ok=True)
    os.environ['MELO_VIET_ROOT']=str(root)
    records=fast_backend.catalog()
    for model in records:
        fast_backend.ensure_model(model,False)
        print('Verified model files:',model['id'],flush=True)
    if prepare_only:return
    samples=json.loads(Path(__file__).with_name('samples.json').read_text(encoding='utf-8'))
    reader=Reader(root,'piper',offline=True)
    report={'status':'running','runtime':'Piper 1.8.0 CPU FP32','platform':'Ubuntu/Linux test, not Windows/Xeon',
        'cached_audio':False,'target_30x_verified':False,'human_listening_quality_verified':False,'results':[]}
    try:
        for model in records:
            voice=next(v for v in fast_backend.voices_for(model['language']) if v['id'].startswith('piper:'+model['id']+':'))
            for repeat in range(2):
                start=time.perf_counter()
                result=reader.request({'op':'render','backend':'piper','engine':'local','language':model['language'],
                    'voice':voice['id'],'text':samples[model['language']],'threads':threads,'output':str(output/(model['id']+'-'+str(repeat)+'.wav'))})
                elapsed=time.perf_counter()-start
                assert .3<result['audio_seconds']<80 and 0<result['peak']<=.951
                report['results'].append({**result,'model':model['id'],'language':model['language'],'round':repeat,
                    'wall_seconds':elapsed,'realtime_multiplier':result['audio_seconds']/elapsed,'threads':threads})
            print('Real offline synthesis passed:',model['id'],flush=True)
            (output/'LOCAL-27-MODEL-QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        report['status']='passed'
    except Exception:
        log=root/'logs/piper.log'
        if log.is_file():
            tail=log.read_text(encoding='utf-8',errors='replace')[-2500:].replace('%','%25').replace('\n','%0A').replace('\r','%0D')
            print('::error title=Local model synthesis::'+tail,flush=True)
        raise
    finally:
        reader.close();(output/'LOCAL-27-MODEL-QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    # Test the real ordered parallel chunk pipeline and persistent history too.
    studio=Studio(root,offline=True);studio.settings(1)
    def wait(ident):
        end=time.monotonic()+180
        while time.monotonic()<end:
            job=studio.jobs[ident]
            if job['status'] in {'done','error','cancelled'}:
                if job['status']!='done':raise RuntimeError(job.get('error','Pipeline failed'))
                return job
            time.sleep(.1)
        raise TimeoutError('Pipeline timeout')
    results=[]
    try:
        text=('Hola a todos. Hoy vamos a contar una historia interesante sobre un viaje a España. La voz debe ser clara y natural, con una pronunciación correcta. ')*6
        request={'op':'render','engine':'local','local_provider':'fast','language':'ES','voice':fast_backend.voices_for('ES')[0]['id'],
            'text':text,'name':'Public Spanish pipeline','threads':1,'chunk_workers':4,'chunk_size':180,'use_cache':False}
        for repeat in range(2):
            job=wait(studio.start(request)['id'])
            assert job['cache_hits']==0 and job['fresh_inference'] and job['completed_chunks']==job['total_chunks']
            results.append({k:job[k] for k in ('audio_seconds','processing_seconds','model_load_seconds','realtime_multiplier','cache_hits','total_chunks','parallel_chunks','fresh_inference')})
        request['use_cache']=True;job=wait(studio.start(request)['id'])
        assert job['cache_hits']==job['total_chunks']
        results.append({k:job[k] for k in ('audio_seconds','processing_seconds','realtime_multiplier','cache_hits','total_chunks','parallel_chunks','fresh_inference')})
    finally:
        studio.close()
    (output/'PIPELINE-FAST-QA.json').write_text(json.dumps({'status':'passed','target_30x_verified':False,'results':results},indent=2),encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True)
    p.add_argument('--prepare-only',action='store_true');p.add_argument('--threads',type=int,default=4)
    a=p.parse_args();main(a.root,a.output,a.prepare_only,a.threads)
