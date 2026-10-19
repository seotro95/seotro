from pathlib import Path
from unittest.mock import Mock
from fastapi.testclient import TestClient
import app
from test_clones import sample


def local_status(ready=True):
    return {'ready':ready,'model_ready':ready,'dependencies':True,'styles':list(app.cosy_engine.STYLES),
            'reason':'' if ready else 'Chưa tải mô hình; chạy install_clone_ai.bat.'}


def test_ready_local_engine_and_builtin_reference_need_no_transcript(monkeypatch):
    monkeypatch.setattr(app.cosy_engine,'availability',lambda:local_status())
    infer=Mock(return_value=sample())
    monkeypatch.setattr(app.cosy_engine,'synthesize',infer)
    # Local readiness takes precedence even if old remote settings remain.
    monkeypatch.setenv('HMONG_CLONE_URL','https://unused.example/clone')
    with TestClient(app.app) as client:
        state=client.get('/api/status').json()
        assert state['local_cloning'] and state['custom_cloning'] and 'review' in state['clone_styles']
        response=client.post('/api/speech',json={'text':'Nyob zoo','voice':'hmong-white-male','dialect':'mww','emotion':'review'})
        assert response.status_code==200,response.text
        assert response.content[:4]==b'RIFF'
        infer.assert_called_once_with('Nyob zoo',app.BASE/'static'/'voices'/'hmong-white-male.mp3','review',1.0)
        assert client.post('/api/speech',json={'text':'Hello','voice':'hmong-white-male','dialect':'en'}).status_code==422


def test_custom_voice_enroll_and_local_infer_without_transcript(tmp_path,monkeypatch):
    monkeypatch.setattr(app.clone_store,'DATA',tmp_path/'clones')
    monkeypatch.setattr(app.cosy_engine,'availability',lambda:local_status())
    infer=Mock(return_value=sample())
    monkeypatch.setattr(app.cosy_engine,'synthesize',infer)
    with TestClient(app.app) as client:
        response=client.post('/api/clones',data={'name':'My reference','consent':'true'},files={'file':('ref.wav',sample(),'audio/wav')})
        assert response.status_code==201,response.text
        voice=response.json()
        assert voice['transcript']==''
        response=client.post('/api/speech',json={'text':'Nyob zoo','voice':voice['id'],'dialect':'mww'})
        assert response.status_code==200,response.text
        assert Path(infer.call_args.args[1]).is_file()


def test_missing_local_model_reports_actual_blocker(monkeypatch):
    monkeypatch.setattr(app.cosy_engine,'availability',lambda:local_status(False))
    monkeypatch.delenv('HMONG_CLONE_URL',raising=False)
    monkeypatch.delenv('HMONG_TTS_URL',raising=False)
    def infer(*args):raise app.cosy_engine.EngineError('Chưa tải mô hình; chạy install_clone_ai.bat.')
    monkeypatch.setattr(app.cosy_engine,'synthesize',infer)
    with TestClient(app.app) as client:
        response=client.post('/api/speech',json={'text':'Nyob zoo','voice':'hmong-white-female','dialect':'mww'})
        assert response.status_code==503
        assert 'install_clone_ai.bat' in response.json()['detail']
