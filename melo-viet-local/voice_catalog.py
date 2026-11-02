"""Voice labels from real presets; missing gender is never inferred from pitch."""
import json
from pathlib import Path

ONLINE_LOCALES={'VI':'vi-VN','EN':'en-US','FR':'fr-FR','ES':'es-ES','JP':'ja-JP','KR':'ko-KR','ZH':'zh-CN',
 'RU':'ru-RU','DE':'de-DE','IT':'it-IT','PT':'pt-PT','NL':'nl-NL','PL':'pl-PL','HI':'hi-IN','SV':'sv-SE',
 'DA':'da-DK','FI':'fi-FI','NO':'nb-NO','CS':'cs-CZ','SK':'sk-SK','HU':'hu-HU','RO':'ro-RO','TR':'tr-TR',
 'AR':'ar-JO','FA':'fa-IR','ID':'id-ID','CA':'ca-ES'}


def gender(value):
    return {'male':'Male','female':'Female'}.get(str(value).lower(),'Unknown')


def vietnamese_presets(root):
    voices=[]
    for path in (Path(root)/'envs/viet/lib').glob('python*/site-packages/vieneu/assets/voices_v3_turbo.json'):
        try:
            data=json.loads(path.read_text(encoding='utf-8'))
            for name,info in data.get('presets',{}).items():
                voices.append({'id':name,'name':'VieNeu Turbo · '+name,'gender':gender(info.get('gender')),
                    'description':info.get('description',''),'backend':'viet','locale':'vi-VN'})
        except (OSError,ValueError):pass
        break
    return voices
