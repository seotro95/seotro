"""Live verification of every requested locale, preserving individual service errors."""
import argparse,json,re,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'melo-viet-local'))
from app import Studio
from check_online import TEXTS

p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);a=p.parse_args()
studio=Studio(a.root);studio.settings(1)
report={'platform':'Ubuntu 22.04 CI, not Windows/Xeon','text':'Public greetings only','target_30x_verified':False,
        'human_listening_quality_verified':False,'results':[],'status':'unavailable'}
def wait(ident,timeout=150):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        job=studio.jobs[ident]
        if job['status'] in {'done','error','cancelled'}:return job
        time.sleep(.1)
    studio.cancel(ident);return {'status':'error','error':'Service timeout'}
def sanitize(text):
    text=re.sub(r'https?://\S+|wss?://\S+','[service URL]',str(text))
    return text[:900]
try:
    catalog=wait(studio.start({'op':'catalog','engine':'edge'})['id'])
    if catalog['status']!='done':raise RuntimeError('catalog unavailable')
    report.update(catalog_voice_count=len(catalog['voices']),catalog_locale_count=len(catalog['locales']))
    for locale,text in TEXTS.items():
        voices=[v for v in catalog['voices'] if v['locale']==locale]
        entry={'locale':locale,'attempts':[],'status':'unavailable'}
        # If one actual preset fails, check another real preset explicitly; never
        # replace a user's selected voice or pretend the first preset succeeded.
        for voice in voices[:2]:
            job=wait(studio.start({'op':'render','engine':'edge','language':locale,'voice':voice['id'],
                'text':text,'name':'Public independent service test '+locale,'use_cache':False})['id'])
            if job['status']=='done':
                entry['attempts'].append({k:job[k] for k in ('voice','audio_seconds','processing_seconds','realtime_multiplier','cache_hits')})
                entry['status']='passed';break
            entry['attempts'].append({'voice':voice['id'],'status':'error','error':sanitize(job.get('error'))})
            time.sleep(3)
        report['results'].append(entry)
        print('Live locale',locale,entry['status'],flush=True)
        time.sleep(2)
    passed=sum(e['status']=='passed' for e in report['results'])
    report['status']='passed' if passed==len(TEXTS) else 'partial' if passed else 'unavailable'
except Exception as error:
    report['error']=sanitize(error)
finally:
    studio.close();Path(a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
