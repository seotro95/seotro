import json
import subprocess
import pytest
from video_export import output_size
from video_tasks import run
from dubbing import inspect_video


def test_export_dimensions():
    assert output_size(1920,1080,'2160p')==(3840,2160)
    assert output_size(1080,1920,'2160p')==(2160,3840)
    assert output_size(640,480,'2160p')==(2880,2160)
    assert output_size(640,480,'original')==(640,480)
    assert output_size(7680,4320,'original')==(3840,2160)
    assert output_size(1080,1920,'1080p')==(1080,1920)
    assert output_size(1919,1079,'original')==(1918,1078)
    with pytest.raises(ValueError):output_size(1920,1080,'8k')


@pytest.mark.parametrize('action,source_size,expected',[('export','160x90',(3840,2160)),('render','160x90',(3840,2160)),('dub','160x90',(3840,2160)),('export','90x160',(2160,3840))])
def test_real_4k_export(tmp_path,action,source_size,expected):
    videos=tmp_path/'videos';videos.mkdir()
    work=tmp_path/'video_tasks'/'b';work.mkdir(parents=True)
    source=videos/'a.source'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'color=c=blue:size={source_size}:rate=5:duration=0.4','-c:v','libx264','-f','mp4',str(source)],check=True)
    (videos/'a.json').write_text(json.dumps(inspect_video(source)))
    path=work/'job.json';path.write_text(json.dumps({'video_id':'a','action':action,'export_resolution':'2160p','cues':[{'start':0,'end':.4,'text':'Xuất 4K Việt Nam'}]}))
    if action=='dub':
        import wave
        from dubbing import mux_video
        (tmp_path/'audio').mkdir()
        audio=work/'speech.wav'
        with wave.open(str(audio),'wb') as target:
            target.setnchannels(1);target.setsampwidth(2);target.setframerate(24000);target.writeframes(b'\x00\x00'*4800)
        mux_video({'id':'b','video_id':'a','export_resolution':'2160p','caption_cues':[{'start':0,'end':.4,'text':'Caption kept'}],'logos':[{'x':10,'y':10,'w':20,'h':10,'mode':'color','color':'#ff0000'}]},audio,work,tmp_path,.2)
        output=tmp_path/'audio'/'b.mp4'
    else:
        run(path)
        output=work/'output.mp4'
    meta=inspect_video(output)
    assert (meta['width'],meta['height'])==expected
    assert abs(meta['duration']-.4)<.01
