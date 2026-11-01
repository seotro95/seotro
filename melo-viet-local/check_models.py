"""Optional real CPU smoke test; downloads public models, emits no private samples."""
import argparse
import json
from pathlib import Path
import time
from app import Reader

TEXTS={'EN':'Hello. This is a test of the English voice on this computer.',
       'FR':'Bonjour. Ceci est un essai de la voix française sur cet ordinateur.',
       'JP':'こんにちは。今日はとても良い天気ですね。',
       'KR':'안녕하세요. 오늘도 좋은 하루 보내세요.',
       'ES':'Hola. Esta es una prueba de la voz en español.',
       'ZH':'你好，这是在本机生成的中文语音测试。',
       'VI':'Xin chào, đây là bản thử giọng tiếng Việt trên máy.'}


def main(root,output,languages):
    root=Path(root);output=Path(output);output.mkdir(exist_ok=True)
    readers={k:Reader(root,k) for k in ('melo','viet')}
    report={'platform':'Linux CPU; not a Windows/Xeon hardware benchmark',
            'real_model_synthesis':True,'private_reference_samples_used':False,
            'human_listening_quality_verified':False,'target_30x_verified':False,'results':[]}
    try:
        for language in languages:
            reader=readers['viet' if language=='VI' else 'melo']
            print('Loading public model:',language,flush=True)
            try:
                voices=reader.request({'op':'voices','language':language,'threads':2})['voices']
                for repeat in range(2):
                    began=time.perf_counter()
                    result=reader.request({'op':'render','language':language,'threads':2,'voice':voices[0]['id'],
                        'text':TEXTS[language],'output':str(output/(language+'-'+str(repeat)+'.wav'))})
                    result['wall_seconds']=time.perf_counter()-began;result['round']=repeat
                    report['results'].append(result)
                    (output/'MODEL-QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
                    print('Generated',language,repeat,'WAV seconds',result['audio_seconds'],'wall seconds',result['wall_seconds'],flush=True)
            except Exception:
                log=root/'logs'/('viet.log' if language=='VI' else 'melo.log')
                tail=log.read_text(encoding='utf-8',errors='replace')[-2400:] if log.exists() else 'No SDK log'
                escaped=tail.replace('%','%25').replace('\r','%0D').replace('\n','%0A')
                print('::error title=Public model smoke test::'+escaped,flush=True)
                raise
    finally:
        for reader in readers.values():reader.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True)
    p.add_argument('--languages',nargs='+',default=list(TEXTS));a=p.parse_args();main(a.root,a.output,a.languages)
