"""Real PCM/FFmpeg checks; fixture synthesis is not a model benchmark."""
import json
from pathlib import Path
import threading
import time
import wave

import numpy as np
import pytest
import app
from documents import parse_document
from timing import RATE, TimedAssembler, timing_plan, verify_parts
from test_studio import body, await_job
from test_local import FakeReader


class ToneReader(FakeReader):
    def one(self, request):
        rate = 44100 if request['language'] in {'FR', 'JP'} else 22050
        count = round(rate*.3)
        samples = (.3*np.sin(2*np.pi*330*np.arange(count)/rate)*32767).astype('<i2')
        with wave.open(request['output'], 'wb') as target:
            target.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
            target.writeframes(samples.tobytes())
        return {'audio_seconds': .3, 'model_load_seconds': 0}
    def request(self, request, cancel=None):
        if request['op'] == 'render_many':
            return {'results': [self.one({**request, **item}) for item in request['entries']]}
        if request['op'] == 'render':
            return self.one(request)
        return super().request(request, cancel)


@pytest.fixture
def studio(tmp_path):
    instance = app.Studio(tmp_path, reader_factory=ToneReader)
    yield instance
    instance.close()


def encoded(studio, job):
    studio.exports.start(job['id'])
    end = time.monotonic()+10
    while time.monotonic() < end:
        if job.get('mp3_status') in {'done','error','cancelled'}:
            assert job['mp3_status'] == 'done', job.get('mp3_error')
            return
        time.sleep(.01)
    pytest.fail('MP3 verification did not finish')


@pytest.mark.parametrize('language', list(app.LOCAL_LABELS))
def test_txt_and_srt_use_identical_samples_independent_of_language(studio, language):
    text = {'JP':'こんにちは。','KR':'안녕하세요.','ZH':'你好。','AR':'مرحبا.'}.get(language, 'Hello 123.')
    srt = '1\n00:00:00,125 --> 00:00:02,345\n'+text+'\n'
    txt = await_job(studio, studio.start(body(text=text, language=language, target_seconds=2.345))['id'])
    timed = await_job(studio, studio.start(body(text=srt, name='source.srt', language=language))['id'])
    for job in (txt, timed):
        assert job['status'] == 'done', job.get('error')
        assert job['timing_mode'] == 'exact' and job['duration_verified'] and job['sync_ok']
        assert job['duration_report']['sample_frames'] == 56280
        assert job['target_30x_verified'] is False
    cues = parse_document((studio.root/'outputs'/timed['id']/'subtitles.srt').read_text(), 'output.srt')['cues']
    assert [(c['start_ms'],c['end_ms']) for c in cues] == [(125,2345)]


@pytest.mark.parametrize('target', [1.001, 2.345])
def test_mp3_is_measured_after_encoding_at_the_same_sample_rate(studio, target):
    job = await_job(studio, studio.start(body(target_seconds=target, text='Hello.'))['id'])
    assert job['status'] == 'done', job.get('error')
    encoded(studio, job)
    report = json.loads((studio.root/'outputs'/job['id']/'mp3-report.json').read_text())
    assert report['sample_rate'] == 24000
    assert report['duration_report']['sample_frames'] == round(target*24000)
    assert report['duration_report']['error_frames'] == 0 and job['mp3_duration_verified']


def test_overlong_text_fails_without_publishing_partial_parts(studio):
    job = await_job(studio, studio.start(body(target_seconds=.05, text='Hello.'))['id'])
    assert job['status'] == 'error' and 'không cắt' in job['error']
    folder = studio.root/'outputs'/job['id']
    assert not list(folder.glob('part-*.wav'))
    assert not (folder/'subtitles.srt').exists()
    assert not (folder/'.timing').exists()


def test_srt_overlap_and_conflicting_target_fail_before_queueing(studio):
    overlapping = '1\n00:00:00,000 --> 00:00:02,000\nA.\n\n2\n00:00:01,000 --> 00:00:03,000\nB.\n'
    with pytest.raises(ValueError, match='chồng'):
        studio.start(body(text=overlapping))
    with pytest.raises(ValueError, match='mốc cuối'):
        studio.start(body(text='1\n00:00:00,000 --> 00:00:02,000\nA.',target_seconds=3))
    assert not studio.jobs


@pytest.mark.parametrize('target', [0,-1,True,float('nan'),float('inf'),604801])
def test_bad_target_is_rejected_without_guessing_from_word_count(studio, target):
    with pytest.raises(ValueError):
        studio.start(body(target_seconds=target))
    assert not studio.jobs


def test_trailing_empty_srt_cue_retains_the_final_clock(studio):
    script='1\n00:00:00,100 --> 00:00:01,000\nHello.\n\n2\n00:00:02,000 --> 00:00:03,000\n\n'
    job=await_job(studio,studio.start(body(text=script))['id'])
    assert job['status']=='done',job.get('error')
    assert job['audio_seconds']==3 and job['sync_report']['error_frames']==0


def test_long_timeline_rolls_exactly_across_wav_parts(tmp_path):
    source=tmp_path/'source.wav'
    x=(np.sin(2*np.pi*330*np.arange(12000)/RATE)*8000).astype('<i2')
    with wave.open(str(source),'wb') as target:
        target.setparams((1,2,RATE,0,'NONE','not compressed'));target.writeframes(x.tobytes())
    document=parse_document('All words remain.')
    assembler=TimedAssembler(tmp_path,timing_plan(document,target=2.345),part_seconds=.7)
    try:
        assembler.append(source,document['text'])
        result=assembler.finish()
    finally:assembler.close()
    assert len(result['parts'])==4 and result['part_start_seconds']==[0,.7,1.4,2.1]
    assert verify_parts(tmp_path,result['parts'],RATE,56280)['verified']
    for part in result['parts']:
        with wave.open(str(tmp_path/part)) as audio:assert audio.getnframes()<=16800
    captions=parse_document((tmp_path/'subtitles.srt').read_text(),'captions.srt')['cues']
    assert captions[-1]['end_ms']==2345


def test_bad_mp3_verification_keeps_original_wav(studio, monkeypatch):
    import audio_exports
    def fail(*args):raise ValueError('MP3 thực tế sai thời lượng')
    monkeypatch.setattr(audio_exports,'measure_encoded',fail)
    job=await_job(studio,studio.start(body(target_seconds=2,text='Hello.'))['id'])
    studio.exports.start(job['id'])
    end=time.monotonic()+10
    while job.get('mp3_status') not in {'done','error'} and time.monotonic()<end:time.sleep(.01)
    assert job['mp3_status']=='error'
    folder=studio.root/'outputs'/job['id']
    assert (folder/'part-0001.wav').is_file() and not (folder/'voice.mp3').exists()


def test_natural_mode_remains_available_and_cannot_ignore_a_requested_target(studio):
    job=await_job(studio,studio.start(body(text='1\n00:00:04,000 --> 00:00:06,000\nHello.',timing_mode='natural'))['id'])
    assert job['status']=='done' and job['audio_seconds']<4
    with pytest.raises(ValueError,match='bật'):
        studio.start(body(target_seconds=5,timing_mode='natural'))
