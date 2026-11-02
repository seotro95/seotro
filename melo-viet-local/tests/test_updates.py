import io
import json
from pathlib import Path
import subprocess
import threading
import time
import urllib.request
import wave
import zipfile

import numpy as np
import pytest

import app
from documents import convert_audio,parse_document
from speaking import speech_plan
from test_local import FakeReader
from test_studio import body,await_job


def wait_mp3(studio,ident):
    deadline=time.monotonic()+12
    while time.monotonic()<deadline:
        job=studio.jobs[ident]
        if job.get('mp3_status') in {'done','error','cancelled','interrupted'}:return job
        time.sleep(.02)
    raise AssertionError('Timed out exporting MP3')


@pytest.fixture
def studio(tmp_path):
    s=app.Studio(tmp_path,reader_factory=FakeReader)
    yield s
    s.close()


def test_explicit_emphasis_keeps_all_words_and_merges_punctuation():
    original='Hello **kind friends**! We are **very happy**.'
    document,units=speech_plan(parse_document(original),120,'friendly',True,True)
    assert document['text']=='Hello kind friends! We are very happy.'
    assert ''.join(u['text'] for u in units)==document['text']
    assert all(any(c.isalnum() for c in u['text']) for u in units)
    assert sum(u['emphasis'] for u in units)==2
    assert all(u['speed_scale']<1 and u['gain_db']>0 for u in units if u['emphasis'])


def test_unmatched_marks_are_rejected_only_when_enabled():
    doc=parse_document('Text **not closed')
    with pytest.raises(ValueError,match='khép kín'):speech_plan(doc,emphasis=True)
    plain,units=speech_plan(doc,emphasis=False)
    assert plain['text']=='Text **not closed'


@pytest.mark.parametrize('text',['“**Hello**!”','**Xin chào**.','**こんにちは**。','**안녕하세요**!'])
def test_emphasis_never_sends_punctuation_only_to_a_model(text):
    doc,units=speech_plan(parse_document(text),emphasis=True)
    assert len(units)==1 and '**' not in units[0]['text']


def test_plain_pacing_keeps_the_previous_chunking_and_duration(studio):
    j=await_job(studio,studio.start(body())['id'])
    assert j['status']=='done' and j['total_chunks']==1 and j['audio_seconds']==pytest.approx(.1)
    assert j['progress']==1 and j['stage']=='done'


def test_emphasis_output_srt_and_script_contain_words_not_markup(studio):
    j=await_job(studio,studio.start(body(text='Hello **kind friends**!',emphasis=True,expressive=True))['id'])
    assert j['status']=='done'
    folder=studio.root/'outputs'/j['id']
    assert (folder/'script.txt').read_text()=='Hello kind friends!'
    assert '**' not in (folder/'subtitles.srt').read_text()


def test_mp3_export_is_real_audio_and_keeps_the_original_wav(studio):
    j=await_job(studio,studio.start(body())['id']);ident=j['id'];wave_path=studio.root/'outputs'/ident/'part-0001.wav';before=wave_path.read_bytes()
    studio.exports.start(ident);job=wait_mp3(studio,ident)
    assert job['mp3_status']=='done' and job['mp3_progress']==1
    target=studio.root/'outputs'/ident/'voice.mp3'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=codec_name,sample_rate','-of','json',str(target)]))
    assert info['streams'][0]['codec_name']=='mp3' and info['streams'][0]['sample_rate']=='44100'
    assert wave_path.read_bytes()==before
    assert studio.exports.start(ident)['mp3_status']=='done'


def test_mp3_combines_multiple_wav_parts_without_reading_them_into_memory(studio):
    j=await_job(studio,studio.start(body())['id']);folder=studio.root/'outputs'/j['id']
    (folder/'part-0002.wav').write_bytes((folder/'part-0001.wav').read_bytes())
    studio.exports.start(j['id']);result=wait_mp3(studio,j['id'])
    assert result['mp3_status']=='done'
    report=json.loads((folder/'mp3-report.json').read_text())
    assert report['source_parts']==2 and report['source_audio_seconds']==pytest.approx(.2)


def test_mp3_handles_data_folder_with_spaces_and_apostrophes(tmp_path):
    root=tmp_path/"Jane's voice studio";s=app.Studio(root,reader_factory=FakeReader)
    try:
        j=await_job(s,s.start(body())['id']);s.exports.start(j['id'])
        assert wait_mp3(s,j['id'])['mp3_status']=='done'
    finally:s.close()


def test_old_flat_wav_can_be_exported_to_mp3_and_survives_restart(tmp_path):
    ident='e'*32;outputs=tmp_path/'outputs';outputs.mkdir()
    with wave.open(str(outputs/(ident+'.wav')),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(b'\x01\x00'*2400)
    (outputs/(ident+'.json')).write_text(json.dumps({'audio_seconds':.1,'voice':'old','engine':'old'}))
    s=app.Studio(tmp_path,reader_factory=FakeReader)
    try:
        s.exports.start(ident);assert wait_mp3(s,ident)['mp3_status']=='done'
    finally:s.close()
    reopened=app.Studio(tmp_path,reader_factory=FakeReader)
    try:assert reopened.jobs[ident]['legacy'] and reopened.jobs[ident]['mp3_status']=='done'
    finally:reopened.close()


def test_mp3_failure_does_not_mark_a_finished_wav_failed(studio,monkeypatch):
    j=await_job(studio,studio.start(body())['id'])
    import audio_exports
    def fail(*a,**k):raise FileNotFoundError('synthetic missing ffmpeg')
    monkeypatch.setattr(audio_exports.subprocess,'Popen',fail)
    studio.exports.start(j['id']);job=wait_mp3(studio,j['id'])
    assert job['status']=='done' and job['mp3_status']=='error' and 'ffmpeg' in job['mp3_error']


def test_progress_stays_below_complete_until_final_wav_is_published(studio,monkeypatch):
    events=[];original=studio.update
    def capture(ident,**fields):
        if 'progress' in fields:events.append((fields.get('status','running'),fields['progress']))
        return original(ident,**fields)
    monkeypatch.setattr(studio,'update',capture)
    result=await_job(studio,studio.start(body(text='A '*180,chunk_size=80))['id'])
    assert result['status']=='done'
    assert all(p<1 for status,p in events if status!='done')
    assert events[-1]==('done',1)


def test_mp3_http_download_and_zip_include_finished_export(studio):
    j=await_job(studio,studio.start(body())['id']);studio.exports.start(j['id']);j=wait_mp3(studio,j['id'])
    server=app.ThreadingHTTPServer(('127.0.0.1',0),app.handler(studio));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base='http://127.0.0.1:'+str(server.server_port)
    try:
        with urllib.request.urlopen(base+j['mp3_url']) as r:
            assert r.headers['Content-Type']=='audio/mpeg' and len(r.read())>64
        with urllib.request.urlopen(base+j['bundle_url']) as r:z=zipfile.ZipFile(io.BytesIO(r.read()))
        assert 'voice.mp3' in z.namelist() and 'mp3-report.json' in z.namelist()
    finally:server.shutdown();server.server_close();thread.join(2)
