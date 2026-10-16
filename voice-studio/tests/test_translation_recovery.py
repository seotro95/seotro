import asyncio,json
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import writing
from test_app import studio
from translation import translate_cues


def test_default_cloud_model_recovers_after_generation_404(monkeypatch):
    seen=[]
    async def request(method,url,**kwargs):
        seen.append(url)
        if 'old' in url or writing.DEFAULT_MODELS['gemini'] in url:raise HTTPException(502,'Không tìm thấy model. Hãy kiểm tra tên model.')
        return {'candidates':[{'content':{'parts':[{'text':'{"texts":["Xin chào"]}'}]}}]}
    monkeypatch.setattr(writing,'request_api',request);monkeypatch.setattr(writing,'get_key',lambda _: 'fixture')
    monkeypatch.setattr(writing,'translation_models',AsyncMock(return_value=['gemini-current-flash']))
    original=[{'start':1,'end':4,'text':'Hello'}]
    result=translate_cues(original,'vi','',lambda *a:None,'gemini','en')
    assert result==[{'start':1,'end':4,'text':'Xin chào'}]
    assert original[0]['text']=='Hello' and len(seen)==2
    result=asyncio.run(writing.check_translation_model('gemini',''))
    assert result['model']=='gemini-current-flash' and result['replaced_model']==writing.DEFAULT_MODELS['gemini']


def test_gemini_catalog_pagination_and_generation_capability(monkeypatch):
    async def request(method,url,**kwargs):
        if kwargs['params'].get('pageToken'):return {'models':[{'name':'models/gemini-current-flash','supportedGenerationMethods':['generateContent']}]}
        return {'nextPageToken':'next','models':[{'name':'models/embedding','supportedGenerationMethods':['embedContent']},{'name':'models/gemini-image','supportedGenerationMethods':['generateContent']}]}
    monkeypatch.setattr(writing,'request_api',request);monkeypatch.setattr(writing,'get_key',lambda _: 'fixture')
    assert asyncio.run(writing.translation_models('gemini'))==['gemini-current-flash']


def test_later_batch_failure_does_not_change_original_cues(monkeypatch):
    count=0
    async def request(*args,**kwargs):
        nonlocal count
        count+=1
        if count>1:raise HTTPException(502,'Không tìm thấy model.')
        return {'candidates':[{'content':{'parts':[{'text':json.dumps({'texts':['Đã dịch']*12})}]}}]}
    monkeypatch.setattr(writing,'request_api',request);monkeypatch.setattr(writing,'get_key',lambda _: 'fixture')
    monkeypatch.setattr(writing,'translation_models',AsyncMock(return_value=['other-model']))
    original=[{'start':i,'end':i+1,'text':'Original'} for i in range(13)]
    with pytest.raises(ValueError,match='Phụ đề gốc'):translate_cues(original,'vi','custom-model',lambda *a:None,'gemini')
    assert all(c['text']=='Original' for c in original)


def test_failed_task_exposes_original_cues(studio):
    client,root=studio
    import uuid
    ident=uuid.uuid4().hex;work=root/'video_tasks'/ident;work.mkdir(parents=True)
    (work/'job.json').write_text(json.dumps({'id':ident,'video_id':uuid.uuid4().hex,'status':'error','action':'subtitles','error':'Missing cloud model'}))
    (work/'original.srt').write_text('1\n00:00:01,000 --> 00:00:03,000\nOriginal words\n')
    response=client.get(f'/api/video-tasks/{ident}')
    assert response.status_code==200
    assert response.json()['original_cues']==[{'start':1,'end':3,'text':'Original words'}]


def test_probe_skips_two_listed_but_dead_models_and_uses_generation(monkeypatch):
    calls=[]
    async def request(method,url,**kwargs):
        assert method=='POST' and ':generateContent' in url
        calls.append(url)
        if 'gemini-working-flash' not in url:raise HTTPException(502,'Không tìm thấy model. [HTTP 404]')
        assert kwargs['json']['contents']
        return {'candidates':[{'content':{'parts':[{'text':'{"texts":["OK"]}'}]}}]}
    monkeypatch.setattr(writing,'request_api',request);monkeypatch.setattr(writing,'get_key',lambda _: 'fixture')
    monkeypatch.setattr(writing,'translation_models',AsyncMock(return_value=['gemini-dead-flash','gemini-working-flash']))
    result=asyncio.run(writing.check_translation_model('gemini',''))
    assert result['verified_generation'] and result['model']=='gemini-working-flash' and len(calls)==3


def test_probe_quota_error_does_not_try_other_models(monkeypatch):
    monkeypatch.setattr(writing,'get_key',lambda _: 'fixture')
    request=AsyncMock(side_effect=HTTPException(502,'Đã hết hạn mức. [HTTP 429]'))
    models=AsyncMock(return_value=['another-model'])
    monkeypatch.setattr(writing,'request_api',request);monkeypatch.setattr(writing,'translation_models',models)
    with pytest.raises(HTTPException,match='429'):asyncio.run(writing.check_translation_model('gemini',''))
    assert request.await_count==1 and models.await_count==0


def test_runtime_skips_two_dead_models_without_mutating_cues(monkeypatch):
    async def request(method,url,**kwargs):
        if 'gemini-working-flash' not in url:raise HTTPException(502,'Không tìm thấy model.')
        return {'candidates':[{'content':{'parts':[{'text':'{"texts":["Xin chào"]}'}]}}]}
    monkeypatch.setattr(writing,'get_key',lambda _: 'fixture');monkeypatch.setattr(writing,'request_api',request)
    monkeypatch.setattr(writing,'translation_models',AsyncMock(return_value=['gemini-2.5-flash-lite','gemini-working-flash']))
    cues=[{'start':1,'end':4,'text':'Hello'}]
    assert translate_cues(cues,'vi','',lambda *a:None,'gemini')[0]['text']=='Xin chào'
    assert cues[0]['text']=='Hello'


def test_cloud_error_keeps_google_reason_but_redacts_api_key(monkeypatch):
    import httpx
    secret='AIzaFixtureSecret0123456789'
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def request(self,*args,**kwargs):return httpx.Response(404,json={'error':{'message':'models/test is not found for API version v1beta; key='+secret}})
    monkeypatch.setattr(writing.httpx,'AsyncClient',Client)
    with pytest.raises(HTTPException) as exc:asyncio.run(writing.request_api('POST','https://generativelanguage.googleapis.com/v1beta/models/test:generateContent',headers={'x-goog-api-key':secret}))
    assert 'v1beta' in exc.value.detail and '[HTTP 404]' in exc.value.detail and secret not in exc.value.detail
