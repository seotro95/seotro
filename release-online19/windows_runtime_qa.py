"""Exercise the shipped Windows runtime with synthetic cloud responses only."""
import argparse
import base64
import io
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
import urllib.request
import wave

REPORT = {'version':'1.13.0','platform':'Windows x64, bundled Python',
          'startup_and_local_api_passed':True,'windows_dpapi_roundtrip_passed':True,
          'credential_not_returned_in_api':True,'native_voice_catalog_count':19,
          'numpy_soundfile_soxr_imported':True,'ffmpeg_pcm_pipeline_passed':True,
          'cloud_pipeline_with_synthetic_wav_passed':True,'new_job_after_old_cancellation_passed':True,
          'azure_network_requests_sent':0,'live_azure_synthesis_tested':False,
          'voice_quality_listening_verified':False,'target_30x_verified':False}


def main(root, report):
    assert os.name=='nt'
    root=Path(root).resolve();data=Path(os.environ['VOICE_STUDIO_DATA_DIR']).resolve()
    sys.path.insert(0,str(root/'app'))
    import azure_speech as azure
    import numpy
    import soundfile
    import soxr
    key='qaSyntheticKeyForDpapiOnly00000000'
    azure.save_configuration(data,'southeastasia',key)
    assert azure.credentials(data)==('southeastasia',key)
    encrypted=json.loads((data/'settings/azure-speech.json').read_text())
    assert encrypted['protection']=='windows-dpapi'
    assert key.encode() not in base64.b64decode(encrypted['payload'])
    azure.clear_configuration(data)
    with __import__('socket').socket() as socket:
        socket.bind(('127.0.0.1',0));port=socket.getsockname()[1]
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def api(route, payload=None, method=None):
        request=urllib.request.Request(f'http://127.0.0.1:{port}'+route,
            data=None if payload is None else json.dumps(payload).encode(),
            headers={'Content-Type':'application/json'},method=method)
        with opener.open(request,timeout=10) as response:return json.load(response)
    log=Path(report).with_suffix('.server.log')
    with log.open('w',encoding='utf-8') as stream:
        server=subprocess.Popen([sys.executable,'-s','-X','utf8','-m','uvicorn','app:app',
            '--host','127.0.0.1','--port',str(port),'--no-access-log'],cwd=root/'app',stdout=stream,stderr=stream)
        try:
            for _ in range(160):
                assert server.poll() is None,'Server exited: '+log.read_text(encoding='utf-8')
                try:
                    config=api('/api/config');break
                except (OSError,ValueError):time.sleep(.25)
            else:raise AssertionError('Server startup timeout')
            assert config['version']=='1.13.0' and config['distribution_profile']=='online-19'
            voices=api('/api/voices')['voices'];assert len(voices)==19
            assert all(v['engine']=='azure' and not v['ready'] for v in voices)
            state=api('/api/online/azure',{'region':'southeastasia','key':key},'PUT')
            assert state['configured'] and not state['verified'] and key not in json.dumps(state)
            assert key not in json.dumps(api('/api/config'))
        finally:
            server.terminate()
            try:server.wait(timeout=15)
            except subprocess.TimeoutExpired:server.kill();server.wait(timeout=10)
    buffer=io.BytesIO()
    pcm=b''.join(struct.pack('<h',round(4500*math.sin(2*math.pi*220*i/24000))) for i in range(4800))
    with wave.open(buffer,'wb') as audio:
        audio.setparams((1,2,24000,0,'NONE','not compressed'));audio.writeframes(pcm)
    wav=buffer.getvalue()
    records=[{'ShortName':v['speaker'],'Locale':v['locale'],'VoiceType':'Neural','Status':'GA'} for v in azure.VOICES]
    def synthetic_request(region,secret,route,**kwargs):
        assert region=='southeastasia' and secret==key
        return json.dumps(records).encode() if route=='voices/list' else wav
    azure._request=synthetic_request
    azure.check_connection(data)
    import worker
    job={'id':'cloud-pipeline-qa','text':'안녕하세요. [pause=0.1] 반갑습니다. [pause=0.1] 감사합니다. [pause=0.1] 좋은 하루 보내세요.',
         'input_format':'txt','engine':'azure','voice_id':'azure-ko-KR-InJoon','speaker':'ko-KR-InJoonNeural',
         'language':'ko','format':'wav','speed':1,'delivery':'natural','paragraph_pause':0,
         'nano_parallel':4,'nano_threads':1,'model_memory':'remote','segment_plan':'azure-packed-v1',
         'audio_fit_backend':'ffmpeg','resource_profile':'maximum'}
    try:
        worker.render(job)
        result=json.loads((data/'parts'/job['id']/'result.json').read_text())
        assert result['execution_settings']['device']=='cloud' and result['execution_settings']['workers']==4
        assert .79 <= result['spoken_audio_seconds'] <= .81
        (data/'parts'/job['id']/'cancel.flag').touch()
        worker.render({**job,'id':'next-job-after-cancellation','nano_parallel':1})
        assert (data/'parts/next-job-after-cancellation/result.json').is_file()
        subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(data/'audio'/f"{job['id']}.wav"),'-f','null','-'],check=True,timeout=30)
    finally:
        worker.close_nano_pool();azure.clear_configuration(data)
    Path(report).write_bytes((json.dumps(REPORT,sort_keys=True,indent=2)+'\n').encode('utf-8'))
    print('Windows bundle, DPAPI, local API and synthetic cloud PCM pipeline verified. No Azure audio request was sent.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--report',required=True)
    a=p.parse_args();main(a.root,a.report)
