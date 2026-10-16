import asyncio,json,uuid,wave,subprocess
from unittest.mock import AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from test_app import studio
import writing
import app


def test_export_voice_all_formats(studio):
    client,root=studio
    ident=uuid.uuid4().hex
    app.write_json(root/'jobs'/f'{ident}.json',{'id':ident,'status':'done','format':'wav'})
    source=root/'audio'/f'{ident}.wav'
    with wave.open(str(source),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(24000);f.writeframes(b'\x00\x20'*24000)
    (root/'audio'/f'{ident}.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\nこんにちは。\n',encoding='utf-8')
    c=client
    response=c.get(f'/api/jobs/{ident}/export.mp3');assert response.status_code==200 and response.headers['content-type']=='audio/mpeg'
    result=subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_name','-of','json',str(root/'audio'/f'{ident}.mp3')],capture_output=True,check=True)
    assert json.loads(result.stdout)['streams'][0]['codec_name']=='mp3'
    assert c.get(f'/api/jobs/{ident}/export.wav').content==source.read_bytes()
    assert c.get(f'/api/jobs/{ident}/export.txt').text=='こんにちは。\n'
    assert '00:00:01,000' in c.get(f'/api/jobs/{ident}/export.srt').text
    assert c.get(f'/api/jobs/{ident}/export.exe').status_code==422
    app.write_json(root/'jobs'/f'{ident}.json',{'id':ident,'status':'running','format':'wav'})
    assert c.get(f'/api/jobs/{ident}/export.mp3').status_code==409


def test_preflight_local_model_missing_and_default_recovery(monkeypatch):
    monkeypatch.setattr(writing,'local_status',AsyncMock(return_value={'models':['installed:latest']}))
    result=asyncio.run(writing.check_translation_model('ollama','qwen3:4b'))
    assert result['model']=='installed:latest'
    import pytest
    with pytest.raises(HTTPException) as exc:asyncio.run(writing.check_translation_model('ollama','missing:7b'))
    assert exc.value.status_code==503 and 'model dịch' in exc.value.detail
    monkeypatch.setattr(writing,'local_status',AsyncMock(return_value={'models':[]}))
    with pytest.raises(HTTPException):asyncio.run(writing.check_translation_model('ollama',''))


def test_preflight_cloud_failure_names_provider_and_model(monkeypatch):
    monkeypatch.setattr(writing,'get_key',lambda _: 'fixture-key')
    monkeypatch.setattr(writing,'request_api',AsyncMock(side_effect=HTTPException(502,'Không tìm thấy model.')))
    import pytest
    with pytest.raises(HTTPException) as exc:asyncio.run(writing.check_translation_model('gemini','missing-model'))
    assert 'gemini' in exc.value.detail and 'missing-model' in exc.value.detail and 'model giọng' in exc.value.detail
