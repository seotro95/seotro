import importlib,json,wave
from unittest.mock import patch
import numpy as np
import pytest
from subtitles import parse_srt
from test_app import studio  # noqa: F401

@pytest.mark.parametrize('language,text',[('vi','Xin chào.'),('en-US','Hello world.'),('ja','こんにちは。'),('ko','안녕하세요.'),('zh','你好。'),('fr','Bonjour.')])
def test_strict_subtitle_timing_and_pcm_boundaries(tmp_path,monkeypatch,language,text):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR',str(tmp_path));worker=importlib.import_module('worker');monkeypatch.setattr(worker,'DATA',tmp_path);(tmp_path/'audio').mkdir()
    srt=f'1\n00:00:00,500 --> 00:00:01,500\n{text}\n\n2\n00:00:02,000 --> 00:00:03,000\n{text}\n'
    def synth(text,path):
        with wave.open(str(path),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(24000);f.writeframes(b'\x00\x20'*18000)
    worker.render({'id':'aligned','text':srt,'input_format':'srt','engine':'vieneu' if language in {'vi','en-US','en-GB'} else 'qwen','language':language,'format':'wav','speed':1,'cue_fit':'strict','max_cue_tempo':2},synth)
    assert parse_srt((tmp_path/'audio/aligned.srt').read_text())==parse_srt(srt)
    report=json.loads((tmp_path/'parts/aligned/alignment.json').read_text());assert report['sync_ok'] and len(report['cues'])==2
    with wave.open(str(tmp_path/'audio/aligned.wav')) as f:samples=np.frombuffer(f.readframes(f.getnframes()),np.int16)
    assert not np.any(samples[:12000]) and np.any(samples[12000:30000])
    assert not np.any(samples[30000:48000]) and np.any(samples[48000:66000]) and not np.any(samples[66000:])
    assert report['cues'][0]['spoken_start']==.5 and report['cues'][1]['spoken_start']==2


def test_fit_up_to_two_times_and_report_unfit_cue(tmp_path,monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR',str(tmp_path));worker=importlib.import_module('worker');monkeypatch.setattr(worker,'DATA',tmp_path);(tmp_path/'audio').mkdir()
    def synth(text,path):
        with wave.open(str(path),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(24000);f.writeframes(b'\x00\x20'*42000)
    job={'id':'fit2','text':'1\n00:00:00,000 --> 00:00:01,000\nHello.','input_format':'srt','engine':'vieneu','format':'wav','speed':1,'cue_fit':'strict','max_cue_tempo':2}
    worker.render(job,synth)
    report=json.loads((tmp_path/'parts/fit2/alignment.json').read_text());assert report['sync_ok'];assert 1.7<report['cues'][0]['tempo']<=2
    with pytest.raises(ValueError,match='Câu SRT 1'):worker.render({**job,'id':'fail','max_cue_tempo':1.5},synth)
    failed=json.loads((tmp_path/'parts/fail/alignment.json').read_text());assert failed['failed_cue']==1 and not failed['sync_ok'] and failed['cues'][0]['status']=='too_long'


def test_alignment_api_and_model_error_messages(studio):
    import app,worker
    client,root=studio;ident='f'*32;app.write_json(root/'jobs'/f'{ident}.json',{'id':ident,'status':'error'})
    assert client.get(f'/api/jobs/{ident}/alignment').json()['pending']
    work=root/'parts'/ident;work.mkdir(parents=True);app.write_json(work/'alignment.json',{'cues':[],'sync_ok':False,'failed_cue':1})
    assert client.get(f'/api/jobs/{ident}/alignment').json()['failed_cue']==1
    assert 'Thiếu thư viện' in worker.voice_error(ModuleNotFoundError(name='vieneu'))
    assert 'RAM' in worker.voice_error(RuntimeError('CUDA out of memory'))


def test_full_voice_preview_seeks_the_same_audio_timeline(tmp_path):
    import subprocess
    from video_tasks import run
    from dubbing import inspect_video
    (tmp_path/'videos').mkdir();(tmp_path/'audio').mkdir();work=tmp_path/'video_tasks'/'proof';work.mkdir(parents=True)
    source=tmp_path/'videos'/'a.source'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=blue:s=160x90:r=10:d=3','-c:v','libx264','-f','mp4',str(source)],check=True)
    (tmp_path/'videos'/'a.json').write_text(json.dumps(inspect_video(source)))
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=400:duration=1','-f','lavfi','-i','sine=frequency=800:duration=2','-filter_complex','[0:a][1:a]concat=n=2:v=0:a=1[a]','-map','[a]',str(tmp_path/'audio'/'voice.wav')],check=True)
    job=work/'job.json';job.write_text(json.dumps({'action':'preview','video_id':'a','voice_job_id':'voice','preview_start':1.2,'preview_seconds':1}))
    run(job)
    samples=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(work/'output.mp4'),'-vn','-ac','1','-ar','16000','-f','f32le','-']),np.float32)
    hz=np.argmax(abs(np.fft.rfft(samples)))*16000/len(samples);assert abs(hz-800)<10
