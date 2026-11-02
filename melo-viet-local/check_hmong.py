"""Verify the installed native Hmong reader and RPA samples; do not redistribute weights."""
import argparse,json,time
from pathlib import Path
from app import Reader,Studio
from hmong_backend import REPO,REVISION,VOICE

def main(root,output):
    root=Path(root);output=Path(output);output.mkdir(parents=True,exist_ok=True);reader=Reader(root,'hmong')
    report={'status':'running','repo':REPO,'revision':REVISION,'gender':'Unknown','dialect_verified_by_native_listener':False,'results':[]}
    try:
        catalog=reader.request({'op':'voices','backend':'hmong','language':'HMN'});assert len(catalog['voices'])==1 and catalog['voices'][0]['gender']=='Unknown'
        for i,text in enumerate(['Nyob zoo, kuv yog Hmoob Dawb. Hnub no peb zoo siab tau ntsib koj.','Kuv zoo siab heev. Peb yog Hmoob Dawb.','Koj puas nyob zoo? Ua tsaug ntau.']):
            t=time.perf_counter();r=reader.request({'op':'render','backend':'hmong','language':'HMN','voice':VOICE,'threads':4,'text':text,'output':str(output/f'hmong-rpa-{i}.wav')})
            assert r['audio_seconds']>.3 and r['sample_rate']==16000 and 0<r['peak']<=.951
            report['results'].append({**r,'text':text,'wall_seconds':time.perf_counter()-t})
        report['status']='passed'
    except Exception:
        log=root/'logs/hmong.log'
        if log.is_file():print('::error title=Native Hmong reader::'+log.read_text(errors='replace')[-4000:].replace('%','%25').replace('\n','%0A'),flush=True)
        raise
    finally:reader.close();(output/'HMONG-QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    # Ensure offline restarts use the downloaded snapshot and route through the real app.
    studio=Studio(root,offline=True);studio.settings(1)
    try:
        j=studio.start({'engine':'local','local_provider':'fast','language':'HMN','voice':VOICE,'text':'Nyob zoo. Ua tsaug ntau.','name':'Hmong offline restart','threads':4,'use_cache':False})
        deadline=time.monotonic()+120
        while studio.jobs[j['id']]['status'] not in {'done','error'} and time.monotonic()<deadline:time.sleep(.1)
        j=studio.jobs[j['id']];assert j['status']=='done',j.get('error');assert j['cache_hits']==0 and j['warnings']
        report['offline_app_restart_passed']=True;(output/'HMONG-QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    finally:studio.close()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);a=p.parse_args();main(a.root,a.output)
