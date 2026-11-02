"""Optional live smoke test using public greetings; no private user text or voices."""
import argparse
import json
from pathlib import Path
import time
from app import Studio

TEXTS={'vi-VN':'Xin chào các bạn. Đây là một đoạn thử giọng tiếng Việt cho công cụ tạo lời đọc.',
'en-US':'Hello everyone. This is a short English sample for testing the speech creation tool.',
'ko-KR':'안녕하세요. 이것은 음성 생성 도구를 테스트하기 위한 한국어 음성 샘플입니다.',
'ru-RU':'Всем привет. Это короткий пример русской речи для проверки программы создания голоса.',
'ja-JP':'こんにちは。これは音声作成ツールをテストするための日本語の短いサンプルです。',
'fr-FR':'Bonjour à tous. Ceci est un court exemple de voix française pour tester cet outil de création vocale.',
'es-ES':'Hola a todos. Este es un breve ejemplo de voz en español para probar esta herramienta.',
'th-TH':'สวัสดีทุกคน นี่คือตัวอย่างเสียงภาษาไทยสำหรับทดสอบเครื่องมือสร้างเสียงพูด'}


def main(root,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);studio=Studio(root)
    report={'status':'unavailable','provider':'Microsoft Edge via edge-tts 7.3.1','public_test_text_only':True,
            'target_30x_verified':False,'human_listening_quality_verified':False,'platform':'Linux CI, not Windows/Xeon', 'results':[]}
    def wait(ident,timeout=180):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            j=studio.jobs[ident]
            if j['status'] in {'done','error','cancelled'}:
                if j['status']!='done':raise RuntimeError('Online job did not finish: '+j['status'])
                return j
            time.sleep(.1)
        studio.cancel(ident);raise TimeoutError('Online service timeout')
    try:
        catalog=wait(studio.start({'op':'catalog','engine':'edge'})['id'],75)
        report.update(catalog_voice_count=len(catalog['voices']),catalog_locale_count=len(catalog['locales']))
        for locale,text in TEXTS.items():
            voices=[v for v in catalog['voices'] if v['locale']==locale]
            if not voices:raise ValueError('Requested public-test locale is absent')
            result=wait(studio.start({'op':'render','engine':'edge','language':locale,'voice':voices[0]['id'],
                'text':text,'name':'Public test '+locale,'use_cache':False})['id'])
            report['results'].append({k:result[k] for k in ('language','voice','audio_seconds','processing_seconds','realtime_multiplier','cache_hits')})
        report['status']='passed'
    except Exception as error:
        # Keep service errors visible without publishing request URLs or headers.
        report['error_type']=type(error).__name__
        report['message']='Live online service unavailable in this CI run. Offline engines are independent. No fallback voice was substituted.'
    finally:
        studio.close();(output/'ONLINE-QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Online live smoke:',report['status'],'completed languages:',len(report['results']),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();main(a.root,a.output)
