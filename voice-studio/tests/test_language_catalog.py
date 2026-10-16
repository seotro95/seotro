import json
from types import SimpleNamespace
from unittest.mock import patch
from language_catalog import LANGUAGES,CORE_LANGUAGES,QWEN_LANGUAGES,RECOGNITION_CODES
from test_app import studio  # noqa: F401


def test_catalog_keeps_ai_capability_truthful(studio):
    import app
    client,_=studio;config=client.get('/api/config').json();assert len(config['subtitle_languages'])==52
    assert {'th','hi','ar','id','km'}<=set(config['subtitle_languages'])
    assert set(config['ai_voice_languages'])==set(CORE_LANGUAGES)
    qwen=[v for v in client.get('/api/voices').json()['voices'] if v['engine']=='qwen']
    assert len(qwen)==9 and {'Serena','Uncle Fu','Dylan','Eric'}<={v['name'] for v in qwen}
    assert all(set(v['languages'])==set(QWEN_LANGUAGES) and 'th' not in v['languages'] for v in qwen)
    assert client.post('/api/speech',json={'text':'test','language':'hi','voice_id':'qw-ryan'}).status_code==422


def test_expanded_asr_and_translation_validation(studio):
    import app
    client,data=studio;ident='a'*32;(data/'videos').mkdir(exist_ok=True);app.write_json(data/'videos'/f'{ident}.json',{'duration':3})
    model=data/'models'/'whisper-base';model.mkdir();(model/'model.bin').write_bytes(b'test')
    with patch('app.executor.submit'):
        assert client.post('/api/video-tasks',json={'video_id':ident,'action':'subtitles','source_language':'hi'}).status_code==202
        assert client.post('/api/video-tasks',json={'video_id':ident,'action':'subtitles','source_language':'xx'}).status_code==422
        assert client.post('/api/video-tasks',json={'action':'translate_text','text':'Hello','target_language':'th','provider':'ollama','model':'local'}).status_code==202


def test_windows_voice_cultures_include_more_languages(monkeypatch):
    import system_voices
    system_voices.installed_voices.cache_clear()
    monkeypatch.setattr(system_voices,'os',SimpleNamespace(name='nt'))
    monkeypatch.setattr(system_voices.shutil,'which',lambda name:'powershell.exe')
    monkeypatch.setattr(system_voices.subprocess,'run',lambda *a,**k:SimpleNamespace(stdout=json.dumps([{'name':'Thai Voice','culture':'th-TH'},{'name':'Hindi Voice','culture':'hi-IN'},{'name':'French Canada','culture':'fr-CA'}])))
    try:
        voices=system_voices.installed_voices();assert [v['languages'][0] for v in voices]==['th','hi','fr'];assert voices[0]['culture']=='th-TH'
    finally:system_voices.installed_voices.cache_clear()
