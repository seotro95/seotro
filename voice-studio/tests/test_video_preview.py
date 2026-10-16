import json
import subprocess
import numpy as np
import pytest
from video_editor import validate_style,write_ass
from video_tasks import run
from dubbing import inspect_video

@pytest.mark.parametrize('style',[{'font':'Arial,Injected'},{'color':'red;movie=x'},{'size':float('nan')},{'size':{}},{'background':'true'},{'position':'left'}])
def test_style_rejects_invalid(style):
    with pytest.raises(ValueError):validate_style(style)

def test_styled_proof_with_logo_and_voice(tmp_path,monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR',str(tmp_path))
    for folder in ['videos','audio','video_tasks']:(tmp_path/folder).mkdir()
    source=tmp_path/'videos'/'source.source'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=320x240:r=10:d=3','-f','lavfi','-i','sine=frequency=1000:duration=3','-c:v','libx264','-c:a','aac','-f','mp4',str(source)],check=True)
    (tmp_path/'videos'/'source.json').write_text(json.dumps(inspect_video(source)))
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=400:duration=1','-y',str(tmp_path/'audio'/'voice.wav')],check=True)
    work=tmp_path/'video_tasks'/'proof';work.mkdir()
    job={'action':'preview','video_id':'source','preview_start':1,'preview_seconds':1,'preview_voice_id':'voice','export_resolution':'original','cues':[{'start':1,'end':2,'text':'PREVIEW'}],'caption_style':{'color':'#ffff00','bold':True,'size':10,'position':'top'},'logos':[{'x':10,'y':100,'w':30,'h':20,'mode':'color','color':'#ff0000'}]}
    path=work/'job.json';path.write_text(json.dumps(job));run(path)
    output=work/'output.mp4';meta=inspect_video(output);assert abs(meta['duration']-1)<.15
    pixels=subprocess.check_output(['ffmpeg','-v','error','-i',str(output),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-']);frame=np.frombuffer(pixels,np.uint8).reshape(240,320,3)
    assert frame[110,20,0]>180 and frame[110,20,2]<60
    yellow=(frame[:,:,0]>150)&(frame[:,:,1]>150)&(frame[:,:,2]<100);assert yellow[:90].sum()>30
    audio=subprocess.check_output(['ffmpeg','-v','error','-i',str(output),'-vn','-ac','1','-ar','16000','-f','f32le','-']);samples=np.frombuffer(audio,np.float32);freq=np.argmax(abs(np.fft.rfft(samples)))*16000/len(samples);assert abs(freq-400)<10
    text=(work/'captions.ass').read_text();assert 'Arial,24,&H0000ffff'.lower() in text.lower()
