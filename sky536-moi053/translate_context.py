import concurrent.futures
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

R = Path(__file__).parent
D = R / 'documents'
S = R / 'voice/scripts'
chapters = json.loads((D / 'LOCALIZATION_SOURCE_CHAPTERS.json').read_text())
languages = {'vi-VN':'vi','es-ES':'es','fr-FR':'fr','ja-JP':'ja','ko-KR':'ko','de-DE':'de','it-IT':'it',
             'pt-PT':'pt-PT','nl-NL':'nl','pl-PL':'pl','sv-SE':'sv','da-DK':'da','fi-FI':'fi','nb-NO':'no','cs-CZ':'cs'}

def translate(text, language):
    query = urllib.parse.urlencode({'client':'gtx','sl':'en','tl':language,'dt':'t','q':text})
    for attempt in range(4):
        try:
            request = urllib.request.Request('https://translate.googleapis.com/translate_a/single?' + query,
                                             headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(request, timeout=40) as response:
                result = json.load(response)
            translated = ''.join(x[0] for x in result[0] if x and x[0]).replace('\u200b','').strip()
            assert translated != text and len(translated) > len(text) * .1
            return translated
        except urllib.error.HTTPError as error:
            if error.code in (401,403,429):
                print('TRANSLATION_SERVICE_STOP',error.code,'Retry-After',error.headers.get('Retry-After'),flush=True)
                raise
            if attempt == 3:
                raise
            time.sleep(min(8, 2 ** attempt))
        except Exception:
            if attempt == 3:
                raise
            time.sleep(min(8, 2 ** attempt))

def job(item):
    locale, language = item
    path = S / (locale + '.context-draft.json')
    rows = json.loads(path.read_text()) if path.exists() else []
    for chapter in chapters[len(rows):]:
        body = translate(chapter['voice'], language)
        rows.append({**chapter, 'source_voice':chapter['voice'], 'voice':body, 'locale':locale,
                     'translation_method':'Google automated language-country draft; context review pending; not independently native-reviewed'})
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'translated':locale,'chapters':len(rows),'total':13}), flush=True)
        time.sleep(3.5)
    assert len(rows) == 13 and rows[-1]['end'] == 1332
    return locale

if __name__ == '__main__':
    for locale, language in languages.items():
        if locale=='vi-VN':continue
        print('DRAFT_DONE',job((locale,language)),flush=True)
