import io
import json
from pathlib import Path
import threading
import time
import urllib.request
import urllib.error
import wave
import zipfile

import numpy as np
import pytest

import app
from documents import Assembler, MAX_CHARS, convert_audio, parse_document, plan_document, split_text
from test_local import FakeReader


def body(**changes):
    return {'op':'render','language':'VI','voice':'VI','text':'Xin chào. Đây là một bản thử.', **changes}


def await_job(studio,ident):
    until=time.monotonic()+8
    while time.monotonic()<until:
        result=studio.jobs[ident]
        if result['status'] in app.TERMINAL:return result
        time.sleep(.01)
    raise AssertionError('Timed out '+str(studio.jobs[ident]))


@pytest.fixture
def studio(tmp_path):
    s=app.Studio(tmp_path,reader_factory=FakeReader)
    yield s
    s.close()


@pytest.mark.parametrize('source',['Xin chào. '*1000,'한글日本語中文。'*500,'a'*3000,'x\n\n'*500])
def test_split_preserves_every_character_and_bounds_memory(source):
    chunks=split_text(source,120)
    assert ''.join(chunks)==source
    assert all(0<len(c)<=120 for c in chunks)


def test_million_characters_accepted_without_truncation_and_limit_is_enforced(studio):
    text=('Xin chào. '*100001)[:MAX_CHARS]
    normalized=studio.validate(body(text=text))
    assert len(normalized['text'])==MAX_CHARS
    chunks=plan_document(parse_document(text),480)
    assert ''.join(chunks)==text and len(chunks)>2000
    with pytest.raises(ValueError):studio.validate(body(text=text+'x'))


@pytest.mark.parametrize('text',[
    '1\n00:00:03,000 --> 00:00:02,000\nBad\n',
    '1\n00:61:03,000 --> 00:62:02,000\nBad\n',
    '1\n00:00:00,000 --> wrong\nBad\n'])
def test_invalid_srt_never_falls_back_to_reading_timestamps(text):
    with pytest.raises(ValueError):parse_document(text,'bad.srt')


def test_srt_is_detected_by_content_and_only_dialogue_is_spoken():
    doc=parse_document('\ufeff1\r\n00:00:03,000 --> 00:00:05,000\r\n<i>Bonjour</i> &amp; bonsoir.\r\n\r\n2\r\n00:00:04,000 --> 00:00:08,000\r\nHello<br>world.\r\n','misnamed.txt')
    assert doc['format']=='srt' and doc['text']=='Bonjour & bonsoir.\nHello\nworld.'
    assert len(doc['warnings'])==2
    assert '-->' not in ''.join(plan_document(doc))


def test_history_survives_restart_and_retry_reuses_only_valid_cached_audio(studio):
    ident=studio.start(body())['id'];first=await_job(studio,ident)
    assert first['status']=='done' and first['cache_hits']==0
    second=await_job(studio,studio.resume(ident)['id'])
    assert second['status']=='done' and second['cache_hits']==1 and not second['fresh_inference']
    assert second['target_30x_verified'] is False
    root=studio.root;studio.close()
    reopened=app.Studio(root,reader_factory=FakeReader)
    try:
        assert len(reopened.list_jobs()['jobs'])==2
        assert reopened.jobs[ident]['text_url'].endswith('script.txt')
    finally:reopened.close()


def test_concurrent_jobs_overlap_and_queued_cancel_does_not_cancel_other_jobs(studio):
    entered=threading.Barrier(3);release=threading.Event()
    class Slow(FakeReader):
        def request(self,payload,cancel=None):
            entered.wait(timeout=4);release.wait(4)
            return super().request(payload,cancel)
    studio.reader_factory=Slow
    jobs=studio.start_batch([body(text='First'),body(text='Second'),body(text='Third')])
    entered.wait(timeout=4)
    assert sum(j['status']=='running' for j in studio.jobs.values())==2
    studio.cancel(jobs[2]['id']);release.set()
    assert [await_job(studio,j['id'])['status'] for j in jobs]==['done','done','cancelled']


def test_batch_validation_is_atomic(studio):
    with pytest.raises(ValueError):studio.start_batch([body(),body(speed=float('nan'))])
    assert not studio.jobs


def test_interrupted_job_becomes_resumable_on_restart(tmp_path):
    ident='a'*32;folder=tmp_path/'outputs'/ident;folder.mkdir(parents=True)
    (folder/'job.json').write_text(json.dumps({'id':ident,'status':'running','created_at':'2026-01-01','op':'render'}))
    (folder/'input.json').write_text(json.dumps(body()))
    s=app.Studio(tmp_path,reader_factory=FakeReader)
    try:
        assert s.jobs[ident]['status']=='interrupted'
        assert await_job(s,s.resume(ident)['id'])['status']=='done'
    finally:s.close()


def test_reading_rate_changes_duration_and_preserves_pitch(tmp_path):
    import soundfile as sf
    source=tmp_path/'source.wav';output=tmp_path/'faster.wav';rate=24000
    sf.write(source,.4*np.sin(2*np.pi*330*np.arange(rate*2)/rate),rate,subtype='PCM_16')
    convert_audio(source,output,1.5)
    data,sr=sf.read(output)
    assert 1.25<len(data)/sr<1.4
    spectrum=np.abs(np.fft.rfft(data));peak=np.fft.rfftfreq(len(data),1/sr)[np.argmax(spectrum)]
    assert abs(peak-330)<3


def test_long_output_rolls_into_wav_parts_and_srt_tracks_actual_audio(tmp_path):
    source=tmp_path/'test.wav'
    with wave.open(str(source),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(b'\x01\x00'*2400)
    a=Assembler(tmp_path,part_seconds=.15)
    a.append(source,'First',0);a.append(source,'Second',0);result=a.finish()
    assert result['parts']==['part-0001.wav','part-0002.wav']
    assert result['audio_seconds']==pytest.approx(.2)
    doc=parse_document((tmp_path/'subtitles.srt').read_text(),'output.srt')
    assert doc['cues'][1]['start_ms']==100 and doc['cues'][1]['end_ms']==200


def test_online_is_explicit_and_disabled_in_offline_mode(tmp_path):
    s=app.Studio(tmp_path,True,reader_factory=FakeReader)
    try:
        with pytest.raises(ValueError):s.start(body(engine='edge',language='ru-RU',voice='ru-RU-DmitryNeural'))
        with pytest.raises(ValueError):s.start(body(language='XX'))
    finally:s.close()


def test_downloaded_bundle_and_range_requests_have_exact_audio_and_text(studio):
    server=app.ThreadingHTTPServer(('127.0.0.1',0),app.handler(studio));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base='http://127.0.0.1:'+str(server.server_port)
    try:
        result=await_job(studio,studio.start(body())['id'])
        with urllib.request.urlopen(base+result['bundle_url']) as r:
            archive=zipfile.ZipFile(io.BytesIO(r.read()))
        assert archive.read('script.txt').decode()=='Xin chào. Đây là một bản thử.'
        assert archive.read('part-0001.wav').startswith(b'RIFF')
        assert 'subtitles.srt' in archive.namelist()
        request=urllib.request.Request(base+result['audio_url'],headers={'Range':'bytes=0-3'})
        with urllib.request.urlopen(request) as r:
            assert r.status==206 and r.read()==b'RIFF'
        request=urllib.request.Request(base+result['audio_url'],headers={'Range':'bytes=999999999-'})
        with pytest.raises(urllib.error.HTTPError) as e:urllib.request.urlopen(request)
        assert e.value.code==416
    finally:server.shutdown();server.server_close();thread.join(2)


def test_exported_srt_preserves_input_deadlines_by_default(studio):
    source='1\n00:00:30,000 --> 00:00:35,000\nBonjour.\n\n2\n00:01:00,000 --> 00:01:05,000\nBonsoir.\n'
    result=await_job(studio,studio.start(body(text=source,name='input.srt'))['id'])
    assert result['status']=='done'
    file=studio.root/'outputs'/result['id']/'subtitles.srt'
    cues=parse_document(file.read_text(),'output.srt')['cues']
    assert cues[0]['start_ms']==30000 and cues[0]['end_ms']==35000
    assert cues[1]['start_ms']==60000 and cues[1]['end_ms']==65000
    assert result['audio_seconds']==65 and result['duration_verified'] and result['sync_ok']


def test_bad_cache_is_regenerated_instead_of_exporting_invalid_audio(studio):
    first=await_job(studio,studio.start(body())['id'])
    cache=next((studio.root/'cache/audio').glob('*.wav'));cache.write_bytes(b'broken')
    second=await_job(studio,studio.resume(first['id'])['id'])
    assert second['status']=='done' and second['cache_hits']==0


def test_subtitle_for_each_wav_part_starts_at_its_own_zero(tmp_path):
    source=tmp_path/'test.wav'
    with wave.open(str(source),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(b'\x01\x00'*2400)
    a=Assembler(tmp_path,part_seconds=.15);a.append(source,'First');a.append(source,'Second');a.finish()
    cues=parse_document((tmp_path/'part-0002.srt').read_text(),'part.srt')['cues']
    assert cues[0]['start_ms']==0 and cues[0]['end_ms']==100


def test_rendering_rate_and_pacing_reuse_source_without_repeating_inference(studio):
    first=await_job(studio,studio.start(body())['id'])
    second=await_job(studio,studio.start(body(speed=.75,style='calm'))['id'])
    assert first['cache_hits']==0 and second['cache_hits']==1
    assert second['audio_seconds']>first['audio_seconds']


def test_melo_two_model_cache_and_thread_changes_do_not_reload_weights(monkeypatch):
    import sys
    from types import SimpleNamespace
    import worker
    constructed=[]
    class TTS:
        hps=SimpleNamespace(data=SimpleNamespace(spk2id={'speaker':0}))
        def __init__(self,language,device):constructed.append(language)
    worker.models.clear()
    monkeypatch.setitem(sys.modules,'melo.api',SimpleNamespace(TTS=TTS))
    monkeypatch.setitem(sys.modules,'torch',SimpleNamespace(set_num_threads=lambda count:None))
    try:
        original,_,_=worker.read_model('EN',2)
        worker.read_model('FR',4)
        same,_,load=worker.read_model('EN',8)
        assert same is original and load==0 and constructed==['EN','FR']
        worker.read_model('JP',2)
        assert len(worker.models)==2
        worker.read_model('FR',2)
        assert constructed==['EN','FR','JP','FR']
    finally:worker.models.clear()
