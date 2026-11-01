"""Cloud contract checks use local HTTP stubs, never a real subscription."""
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import urllib.error
import wave
import xml.etree.ElementTree as ET

import pytest

import app
import azure_speech as azure
from test_standalone_api import studio, sine_wave  # noqa: F401
from test_native_voxcpm_ui import run_javascript

KEY = 'a' * 32


def provider_catalog():
    return [{'ShortName': v['speaker'], 'Locale': v['locale'], 'VoiceType': 'Neural', 'Status': 'GA'} for v in azure.VOICES]


@pytest.fixture(autouse=True)
def no_external_requests(monkeypatch):
    monkeypatch.delenv('AZURE_SPEECH_KEY', raising=False)
    monkeypatch.delenv('AZURE_SPEECH_REGION', raising=False)
    monkeypatch.setattr(azure.urllib.request, 'build_opener', lambda *a: (_ for _ in ()).throw(AssertionError('Unexpected network request')))


def prepared(data, monkeypatch):
    azure.save_configuration(data, 'southeastasia', KEY)
    monkeypatch.setattr(azure, '_request', lambda *a, **kw: json.dumps(provider_catalog()).encode())
    state = azure.check_connection(data)
    assert state['verified'] and len(state['available_voices']) == 19


def test_catalog_has_19_distinct_native_voices_and_no_implied_readiness(tmp_path):
    voices = azure.catalog(tmp_path)
    assert len(voices) == len({v['id'] for v in voices}) == 19
    assert {v['languages'][0] for v in voices} == {'en-GB', 'ko', 'ru', 'ja', 'fr', 'es', 'th'}
    assert all(not v['ready'] and v['requires_internet'] for v in voices)
    assert all('Turbo' not in v['name'] and 'Neural' in v['description'] for v in voices)


def test_configuration_is_private_and_invalidated_by_key_or_region_changes(tmp_path, monkeypatch):
    prepared(tmp_path, monkeypatch)
    assert KEY not in json.dumps(azure.status(tmp_path))
    path = tmp_path/'settings/azure-speech.json'
    if os.name != 'nt':assert path.stat().st_mode & 0o077 == 0
    azure.save_configuration(tmp_path, 'eastus', 'b' * 32)
    assert not azure.status(tmp_path)['verified']
    assert not any(v['ready'] for v in azure.catalog(tmp_path))
    assert azure.credentials(tmp_path) == ('eastus', 'b' * 32)
    assert not azure.clear_configuration(tmp_path)['configured']


@pytest.mark.parametrize('region,key', [('https://attacker.example', KEY), ('southeastasia', 'bad\r\nkey'), ('../eastus',KEY)])
def test_configuration_rejects_endpoints_and_header_injection(tmp_path, region, key):
    with pytest.raises(ValueError):azure.save_configuration(tmp_path, region, key)
    assert not (tmp_path/'settings/azure-speech.json').exists()


def test_live_catalog_requires_exact_voice_locale_and_model(tmp_path, monkeypatch):
    azure.save_configuration(tmp_path, 'southeastasia', KEY)
    records = provider_catalog()
    records[0]['Locale'] = 'en-US'; records[1]['VoiceType'] = 'Standard'; records[2]['Status'] = 'Deprecated'
    monkeypatch.setattr(azure, '_request', lambda *a, **kw: json.dumps(records).encode())
    assert len(azure.check_connection(tmp_path)['available_voices']) == 16
    assert not azure.catalog(tmp_path)[0]['ready']
    monkeypatch.setattr(azure, '_request', Mock(side_effect=azure.AzureSpeechError('Connection failed')))
    with pytest.raises(azure.AzureSpeechError):azure.check_connection(tmp_path)
    assert not azure.status(tmp_path)['verified']


@pytest.mark.parametrize('voice', azure.VOICES, ids=lambda v: v['id'])
def test_every_voice_sends_native_unicode_as_escaped_ssml(tmp_path, monkeypatch, voice):
    prepared(tmp_path, monkeypatch)
    request = Mock(return_value=sine_wave())
    monkeypatch.setattr(azure, '_request', request)
    text = '한국어 日本語 ภาษาไทย русский & <audio src="x">test</audio>'
    output = tmp_path/'out.wav'
    speak = azure.create_synthesizer(tmp_path, voice['id'], voice['languages'][0])
    speak(text, output)
    root = ET.fromstring(request.call_args.kwargs['payload'])
    node = list(root)[0]
    assert root.attrib['{http://www.w3.org/XML/1998/namespace}lang'] == voice['locale']
    assert node.attrib['name'] == voice['speaker'] and node.text == text and not list(node)
    assert output.read_bytes() == sine_wave()
    with pytest.raises(ValueError):azure.create_synthesizer(tmp_path,voice['id'],'vi')


def test_cancel_and_invalid_audio_do_not_replace_output(tmp_path, monkeypatch):
    prepared(tmp_path, monkeypatch)
    v=azure.VOICES[3]; output=tmp_path/'out.wav';output.write_bytes(b'old')
    monkeypatch.setattr(azure, '_request', lambda *a, **kw:b'bad audio')
    speak=azure.create_synthesizer(tmp_path,v['id'],v['languages'][0])
    with pytest.raises(azure.AzureSpeechError):speak('안녕하세요.',output)
    assert output.read_bytes()==b'old'
    monkeypatch.setattr(azure,'_request',lambda *a,**kw:sine_wave())
    cancel=tmp_path/'cancel.flag';cancel.touch()
    speak=azure.create_synthesizer(tmp_path,v['id'],v['languages'][0],cancel)
    with pytest.raises(InterruptedError):speak('안녕하세요.',output)
    assert output.read_bytes()==b'old'


@pytest.mark.parametrize('code', [400,401,403,404,429,500])
def test_http_errors_never_echo_provider_body_key_or_private_text(monkeypatch, code):
    error=urllib.error.HTTPError('https://region.tts.speech.microsoft.com',code,'private '+KEY,{},io.BytesIO(b'private '+KEY.encode()))
    send=Mock(side_effect=error)
    monkeypatch.setattr(azure.urllib.request,'build_opener',lambda *a:SimpleNamespace(open=send))
    monkeypatch.setattr(azure.time,'sleep',lambda *a:None)
    monkeypatch.setattr(azure.time,'monotonic',Mock(side_effect=range(100)))
    with pytest.raises(azure.AzureSpeechError) as failure:azure._request('southeastasia',KEY,'v1',payload=b'private text')
    assert KEY not in str(failure.value) and 'private' not in str(failure.value)
    assert send.call_count == (3 if code==429 else 1)


def test_response_cap_and_redirects_protect_payload_and_credentials(monkeypatch):
    response=io.BytesIO(b'x'*300)
    opened=Mock(return_value=response)
    monkeypatch.setattr(azure.urllib.request,'build_opener',lambda *a:SimpleNamespace(open=opened))
    with pytest.raises(azure.AzureSpeechError, match='quá lớn'):azure._request('eastus',KEY,'v1',payload=b'text',maximum=100)
    req=opened.call_args.args[0]
    assert req.full_url=='https://eastus.tts.speech.microsoft.com/cognitiveservices/v1'
    assert req.headers['X-microsoft-outputformat']=='riff-24khz-16bit-mono-pcm'
    with pytest.raises(azure.AzureSpeechError):azure._NoRedirect().redirect_request(req,None,302,'',{},'https://attacker.example/')


def test_api_configure_check_and_delete_never_publish_keys(studio, monkeypatch):
    client,data=studio
    response=client.put('/api/online/azure',json={'region':'southeastasia','key':KEY})
    assert response.status_code==200 and KEY not in response.text
    assert not response.json()['verified']
    assert client.post('/api/speech',json={'voice_id':azure.VOICES[3]['id'],'language':'ko','text':'안녕하세요.'}).status_code==503
    monkeypatch.setattr(azure,'_request',lambda *a,**kw:json.dumps(provider_catalog()).encode())
    assert client.post('/api/online/azure/check').json()['verified']
    assert KEY not in client.get('/api/config').text
    assert KEY not in client.get('/api/voices').text
    assert client.delete('/api/online/azure').json()['configured'] is False
    assert client.put('/api/online/azure',json={'region':KEY,'key':KEY[:4]}).status_code==422
    assert KEY not in client.put('/api/online/azure',json={'region':KEY,'key':KEY[:4]}).text


@pytest.mark.parametrize('voice',azure.VOICES,ids=lambda v:v['id'])
def test_api_queues_only_the_selected_native_voice_with_bounded_cloud_workers(studio,monkeypatch,voice):
    client,data=studio;prepared(data,monkeypatch)
    submit=Mock();monkeypatch.setattr(app.executor,'submit',submit)
    result=client.post('/api/speech',json={'voice_id':voice['id'],'language':voice['languages'][0],'text':'Native speech test.',
                                         'nano_parallel':32,'nano_threads':8,'paragraph_pause':0})
    assert result.status_code==202,result.text
    job=result.json();assert job['engine']=='azure' and job['speaker']==voice['speaker']
    assert job['model_memory']=='remote' and job['nano_parallel']==4 and job['nano_threads']==1
    assert job['segment_plan']=='azure-packed-v1' and KEY not in result.text
    assert KEY not in (data/'jobs'/f"{job['id']}.json").read_text()
    assert client.delete('/api/online/azure').status_code==409
    assert client.post('/api/speech',json={'voice_id':voice['id'],'language':'vi','text':'Wrong language'}).status_code==422
    assert client.post('/api/benchmark',json={'voice_id':voice['id'],'language':voice['languages'][0]}).status_code==202


def test_ui_cloud_defaults_are_bounded_and_never_presented_as_cpu_or_turbo():
    run_javascript(r'''
config={}; $('resource-profile').value='maximum';
const voice={engine:'azure'};
assert.equal(parallelLimit(voice),4);assert.equal(threadLimit(voice),1);
assert.deepEqual(boundedRenderResources(voice,{nano_parallel:32,nano_threads:8}),{nano_parallel:4,nano_threads:1});
assert.equal(renderingPresets(voice).quality.nano_parallel,4);
assert.match(engineName(voice),/Azure Neural/);assert.doesNotMatch(engineName(voice),/Turbo/);
$('resource-profile').value='light';assert.equal(parallelLimit(voice),1);
''')


def test_online_distribution_only_exposes_19_native_voices_and_their_languages(studio,monkeypatch,tmp_path):
    from distribution import distribution_profile
    (tmp_path/'DISTRIBUTION.json').write_text(json.dumps({'schema':1,'profile':'online-19'}))
    assert distribution_profile(tmp_path)=='online-19'
    monkeypatch.setattr(app,'distribution_profile',lambda:'online-19')
    client,_=studio
    voices=client.get('/api/voices').json()['voices']
    assert len(voices)==19 and all(v['engine']=='azure' for v in voices)
    assert set(client.get('/api/config').json()['ai_voice_languages'])=={'en-GB','ko','ru','ja','fr','es','th'}


def test_worker_refreshes_cloud_credentials_and_cancel_flag_for_each_job(monkeypatch,tmp_path):
    import importlib
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR',str(tmp_path))
    worker=importlib.import_module('worker')
    monkeypatch.setattr(worker,'_cached_synth',None);monkeypatch.setattr(worker,'_cached_key',None)
    load=Mock(side_effect=[Mock(),Mock()]);monkeypatch.setattr(worker,'load_synthesizer',load)
    first=worker.get_synthesizer({'id':'one','engine':'azure','voice_id':azure.VOICES[0]['id']})
    assert worker.get_synthesizer({'id':'one','engine':'azure','voice_id':azure.VOICES[0]['id']}) is first
    assert worker.get_synthesizer({'id':'two','engine':'azure','voice_id':azure.VOICES[0]['id']}) is not first
    assert load.call_count==2
