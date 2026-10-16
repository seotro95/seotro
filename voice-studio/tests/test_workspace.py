import importlib
import json
import wave
from unittest.mock import patch
import pytest
from subtitles import parse_srt
from test_app import studio  # noqa: F401

SRT='1\n00:00:00,100 --> 00:00:00,200\nXin chào.\n\n2\n00:00:02,000 --> 00:00:02,100\nCảm ơn.\n'

def test_gap_timing_keeps_words_and_uses_free_space(tmp_path,monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR',str(tmp_path));worker=importlib.import_module('worker');monkeypatch.setattr(worker,'DATA',tmp_path);(tmp_path/'audio').mkdir()
    def synth(text,path):
        with wave.open(str(path),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(24000);f.writeframes(b'\x00\x20'*28800)
    job={'id':'gap','text':SRT,'engine':'vieneu','input_format':'srt','format':'wav','speed':1,'cue_fit':'gap','timeline_seconds':4}
    worker.render(job,synth)
    cues=parse_srt((tmp_path/'audio/gap.srt').read_text());assert [c['text'] for c in cues]==['Xin chào.','Cảm ơn.']
    assert cues[0]['start']==.1 and cues[0]['end']==1.3 and cues[1]['start']==2 and cues[1]['end']==3.2
    with wave.open(str(tmp_path/'audio/gap.wav')) as f:assert abs(f.getnframes()/f.getframerate()-3.2)<.001
    with pytest.raises(ValueError,match='đọc quá dài'):worker.render({**job,'id':'strict','cue_fit':'strict'},synth)


def test_gap_timeline_and_completed_timing_api(studio):
    import app
    client,root=studio
    voice={'id':'sys-test','name':'Test','engine':'system','speaker':'Test','languages':['vi']}
    with patch('app.installed_voices',return_value=[voice]),patch('app.executor.submit'):
        response=client.post('/api/speech',json={'text':SRT,'input_format':'srt','voice_id':'sys-test','language':'vi','cue_fit':'gap','timeline_seconds':1})
        assert response.status_code==422
        response=client.post('/api/speech',json={'text':SRT,'input_format':'srt','voice_id':'sys-test','language':'vi','cue_fit':'gap','timeline_seconds':4})
    assert response.status_code==202;job=response.json();assert client.get(f"/api/jobs/{job['id']}/timing").status_code==409
    job['status']='done';app.write_json(root/'jobs'/f"{job['id']}.json",job);(root/'audio'/f"{job['id']}.srt").write_text(SRT)
    assert client.get(f"/api/jobs/{job['id']}/timing").json()['cues']==parse_srt(SRT)


def test_voice_export_rejects_unfinished_and_oversized_audio(studio):
    import app
    client,root=studio;video='b'*32;voice='c'*32;(root/'videos').mkdir(exist_ok=True)
    app.write_json(root/'videos'/f'{video}.json',{'duration':2})
    for record in [{'status':'running','format':'wav'},{'status':'done','format':'wav','audio_seconds':3}]:
        app.write_json(root/'jobs'/f'{voice}.json',record)
        response=client.post('/api/video-tasks',json={'action':'export','video_id':video,'voice_job_id':voice})
        assert response.status_code==422
