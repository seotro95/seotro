import asyncio
from unittest.mock import AsyncMock
import httpx,pytest
from fastapi import HTTPException
import writing
from translation import translate_cues


def fake_client(monkeypatch,responses):
    calls=[]
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def request(self,*args,**kwargs):
            calls.append((args,kwargs));return responses.pop(0)
    monkeypatch.setattr(writing.httpx,'AsyncClient',Client)
    delay=AsyncMock();monkeypatch.setattr(writing.asyncio,'sleep',delay)
    return calls,delay


def test_busy_retry_succeeds_and_respects_bounded_retry_after(monkeypatch):
    calls,delay=fake_client(monkeypatch,[httpx.Response(503,headers={'Retry-After':'120'}),httpx.Response(200,json={'ok':True})])
    assert asyncio.run(writing.request_api('POST','https://example.test'))=={'ok':True}
    assert len(calls)==2 and delay.await_args.args==(5,)


def test_busy_retry_is_limited_and_keeps_provider_error(monkeypatch):
    calls,delay=fake_client(monkeypatch,[httpx.Response(503,json={'error':{'message':'High demand'}}) for _ in range(3)])
    with pytest.raises(HTTPException) as exc:asyncio.run(writing.request_api('POST','https://example.test'))
    assert len(calls)==3 and delay.await_count==2 and '[HTTP 503]' in exc.value.detail and 'High demand' in exc.value.detail


@pytest.mark.parametrize('status',[401,403,429])
def test_no_retries_on_auth_or_quota(monkeypatch,status):
    calls,delay=fake_client(monkeypatch,[httpx.Response(status,json={'error':{'message':'Rejected'}})])
    with pytest.raises(HTTPException):asyncio.run(writing.request_api('POST','https://example.test'))
    assert len(calls)==1 and delay.await_count==0


def test_busy_preflight_and_runtime_switch_model_within_provider(monkeypatch):
    async def request(method,url,**kwargs):
        if '/working-model:' not in url:raise HTTPException(502,'Overloaded [HTTP 503]')
        return {'candidates':[{'content':{'parts':[{'text':'{"texts":["Xin chào"]}'}]}}]}
    monkeypatch.setattr(writing,'get_key',lambda _: 'fixture');monkeypatch.setattr(writing,'request_api',request)
    monkeypatch.setattr(writing,'translation_models',AsyncMock(return_value=['busy-model','working-model']))
    result=asyncio.run(writing.check_translation_model('gemini','busy-model'))
    assert result['model']=='working-model' and result['verified_generation']
    original=[{'start':1,'end':4,'text':'Hello'}]
    assert translate_cues(original,'vi','busy-model',lambda *a:None,'gemini')[0]['text']=='Xin chào'
    assert original[0]['text']=='Hello'


def test_all_busy_reports_outage_without_blame_on_key(monkeypatch):
    monkeypatch.setattr(writing,'get_key',lambda _: 'fixture')
    request=AsyncMock(side_effect=HTTPException(502,'Overloaded [HTTP 503]'))
    monkeypatch.setattr(writing,'request_api',request);monkeypatch.setattr(writing,'translation_models',AsyncMock(return_value=['other-model']))
    with pytest.raises(HTTPException) as exc:asyncio.run(writing.check_translation_model('gemini','busy-model'))
    assert 'vẫn quá tải' in exc.value.detail and 'API key' not in exc.value.detail
    assert request.await_count==2
