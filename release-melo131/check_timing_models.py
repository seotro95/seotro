"""Actual installed Piper/Supertonic models; no mock speech or bundled new weights."""
import argparse
import html
import json
import os
from pathlib import Path
import sys
import time

TARGET = 60
RATE = 48000


def main(root, output):
    root, output=Path(root),Path(output)
    sys.path.insert(0,str(root/'app'))
    os.environ['MELO_VIET_ROOT']=str(root)
    os.environ['HF_HUB_OFFLINE']='1'
    os.environ['TRANSFORMERS_OFFLINE']='1'
    from app import Studio
    import fast_backend
    from multilingual_backend import LANGUAGES, voices_for
    from local_models import ensure
    from documents import parse_document
    samples=json.loads((root/'app/samples.json').read_text())
    for model in fast_backend.catalog():
        fast_backend.ensure_model(model,True)
    ensure('supertonic3',True)
    studio=Studio(root,offline=True)
    studio.settings(1)
    proof={'status':'running','runtime':'Ubuntu 22.04 / WSL-compatible Python 3.10',
           'source_commit':os.environ.get('GITHUB_SHA'),
           'new_model_downloads':False,'human_pronunciation_verified':False,'results':[]}
    def save():
        output.write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
    def wait(ident, field='status'):
        deadline=time.monotonic()+240
        while time.monotonic()<deadline:
            result=studio.jobs[ident]
            if result.get(field) in {'done','error','cancelled','interrupted'}:
                if result[field]!='done':
                    raise ValueError(result.get('error') or result.get('mp3_error') or 'Voice failed')
                return result
            time.sleep(.1)
        raise TimeoutError('Timed voice job did not finish')
    def check(language, voice, provider):
        text=samples[language]
        row={'language':language,'voice':voice,'provider':provider,'exports':[]}
        for kind in ('txt','srt'):
            content=text if kind=='txt' else '1\n00:00:00,250 --> 00:01:00,000\n'+html.escape(text,quote=False)+'\n'
            request={'engine':'local','local_provider':provider,'language':language,'voice':voice,
                     'text':content,'format':kind,'threads':2,'style':'neutral',
                     'name':language+' '+voice+' '+kind,'use_cache':True}
            if kind=='txt':request['target_seconds']=TARGET
            job=wait(studio.start(request)['id'])
            assert job['sync_ok'] and job['duration_verified']
            assert job['sample_rate']==RATE and job['duration_report']['sample_frames']==TARGET*RATE
            folder=root/'outputs'/job['id']
            if kind=='srt':
                cues=parse_document((folder/'subtitles.srt').read_text(),'file.srt')['cues']
                assert cues[0]['start_ms']==250 and cues[-1]['end_ms']==60000
                studio.exports.start(job['id'])
                job=wait(job['id'],'mp3_status')
                mp3=json.loads((folder/'mp3-report.json').read_text())
                assert mp3['duration_report']['sample_frames']==TARGET*RATE
                assert mp3['duration_report']['error_frames']==0
            row['exports'].append({'input':kind,'wav_seconds':job['audio_seconds'],
                    'wav_frames':job['duration_report']['sample_frames'],
                    'mp3_seconds':job.get('mp3_audio_seconds'),'cache_hits':job['cache_hits']})
        proof['results'].append(row)
        save()
        print('REAL TIMED MODEL PASS:',language,voice,'TXT/WAV and SRT/MP3 exactly 60 seconds',flush=True)
    try:
        piper=[]
        for record in fast_backend.catalog():
            piper.extend(v for v in fast_backend.voices_for(record['language'])
                         if v['id'].startswith('piper:'+record['id']+':'))
        assert len({v['id'] for v in piper})==51
        # Catalog records carry the language for each concrete speaker/model.
        for record in fast_backend.catalog():
            for voice in fast_backend.voices_for(record['language']):
                if voice['id'].startswith('piper:'+record['id']+':'):
                    check(record['language'],voice['id'],'fast')
        for language in LANGUAGES:
            selected=voices_for(language) if language=='EN' else voices_for(language)[:1]
            for voice in selected:
                check(language,voice['id'],'multi')
        proof.update(status='passed',piper_presets=51,supertonic_languages=len(LANGUAGES),
                     all_timed_exports_seconds=TARGET,canonical_sample_rate=RATE,
                     case_count=len(proof['results']))
        save()
        print('ALL ORIGINAL CPU MODELS PASSED:',proof['case_count'],'cases',flush=True)
    except Exception:
        save()
        for log in (root/'logs').glob('*.log'):
            print(log.name,log.read_text(errors='replace')[-2500:],flush=True)
        raise
    finally:
        studio.close()


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--root',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args()
    main(a.root,a.output)
