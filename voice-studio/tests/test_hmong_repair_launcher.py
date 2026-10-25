"""Recovery is checked before setup; reopening a live job does not load Torch."""
from types import SimpleNamespace

import pytest

import hmong_launcher as launcher


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    import bundle_check, hmong_acceleration, hmong_health
    monkeypatch.setattr(launcher,'BASE',tmp_path)
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR',str(tmp_path/'data'))
    monkeypatch.setenv('HMOOB_BACKEND','native')
    monkeypatch.setenv('HMOOB_DEVICE','cpu')
    monkeypatch.setenv('HMOOB_PRECISION','auto')
    monkeypatch.setattr(bundle_check,'validate_bundle',lambda base:None)
    monkeypatch.setattr(hmong_acceleration,'preferred_interpreter',lambda base:None)
    monkeypatch.setattr(launcher,'check_dependencies',lambda:None)
    monkeypatch.setattr(launcher,'check_audio_tools',lambda:None)
    return tmp_path,hmong_health


def test_broken_cuda_preference_falls_back_with_notice_and_keeps_native(tmp_path,monkeypatch,capsys):
    monkeypatch.setenv('HMOOB_DEVICE','cuda')
    monkeypatch.setenv('HMOOB_PRECISION','int8')
    calls=[]
    def preferred(base):
        import os
        calls.append((os.environ['HMOOB_DEVICE'],os.environ['HMOOB_PRECISION']))
        if len(calls)==1:raise RuntimeError('CUDA unavailable')
        return None
    assert launcher.select_interpreter(preferred,'native') is None
    assert calls==[('cuda','fp32'),('cpu','fp32')]
    assert 'CPU' in capsys.readouterr().out


def test_valid_managed_cuda_is_preserved(monkeypatch,tmp_path):
    monkeypatch.setenv('HMOOB_DEVICE','cuda')
    monkeypatch.setenv('HMOOB_PRECISION','auto')
    runtime=tmp_path/'cuda'/'python.exe'
    assert launcher.select_interpreter(lambda base:runtime,'native')==runtime


def test_explicit_cpu_error_is_not_disguised(monkeypatch):
    monkeypatch.setenv('HMOOB_DEVICE','cpu')
    monkeypatch.setenv('HMOOB_PRECISION','auto')
    def failed(base):raise RuntimeError('Invalid runtime')
    with pytest.raises(RuntimeError,match='Invalid runtime'):
        launcher.select_interpreter(failed,'native')


def test_probe_flag_never_downloads_or_checks_model_weights(isolated,monkeypatch):
    root,health=isolated
    calls=[]
    monkeypatch.setattr(health,'run_runtime_probe',lambda base:calls.append(base) or {'ok':True})
    monkeypatch.setattr(launcher.subprocess,'run',lambda *a,**k:pytest.fail('No model command during runtime-only probe'))
    assert launcher.main(['--probe-runtime'])==0
    assert calls==[root]


def test_runtime_failure_stops_before_downloads(isolated,monkeypatch):
    _,health=isolated
    monkeypatch.setattr(health,'run_runtime_probe',lambda base:{'ok':False,'message':'DLL không nạp được'})
    monkeypatch.setattr(launcher.subprocess,'run',lambda *a,**k:pytest.fail('No downloads after broken runtime'))
    with pytest.raises(RuntimeError,match='DLL.*runtime-check.json'):
        launcher.main(['--setup-only'])


def test_explicit_speech_test_checks_runtime_models_then_both_voices(isolated,monkeypatch):
    root,health=isolated
    steps=[]
    monkeypatch.setattr(health,'run_runtime_probe',lambda base:steps.append('runtime') or {'ok':True})
    monkeypatch.setattr(launcher.subprocess,'run',lambda command,**k:steps.append(command[-1]) or SimpleNamespace(returncode=0))
    monkeypatch.setattr(health,'test_voices',lambda base:steps.append('voices') or {'ok':True})
    assert launcher.main(['--test-voice'])==0
    assert steps==['runtime','--verify-only','voices']


def test_failed_speech_test_cannot_print_pass(isolated,monkeypatch,capsys):
    _,health=isolated
    monkeypatch.setattr(health,'run_runtime_probe',lambda base:{'ok':True})
    monkeypatch.setattr(launcher.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0))
    monkeypatch.setattr(health,'test_voices',lambda base:{'ok':False,'message':'Không tạo được mẫu'})
    with pytest.raises(RuntimeError,match='Không tạo được mẫu'):
        launcher.main(['--test-voice'])
    assert 'PASS:' not in capsys.readouterr().out


def test_duplicate_live_server_reuse_skips_second_runtime_probe(isolated,monkeypatch):
    import portable_launcher,hmong_acceleration
    _,health=isolated
    monkeypatch.setattr(portable_launcher,'_existing_studio',lambda data,base:{'pid':123,'url':'http://127.0.0.1:8781'})
    monkeypatch.setattr(portable_launcher,'main',lambda **k:0)
    monkeypatch.setattr(hmong_acceleration,'preferred_interpreter',lambda base:pytest.fail('No extra GPU probe for running job'))
    monkeypatch.setattr(launcher,'check_dependencies',lambda:pytest.fail('Existing server already working'))
    monkeypatch.setattr(health,'run_runtime_probe',lambda base:pytest.fail('No second Torch import near active job'))
    assert launcher.main(['--no-browser'])==0


def test_full_guide_serves_with_exact_script_and_style_hashes(monkeypatch):
    import app,base64,hashlib,re
    from fastapi.testclient import TestClient
    monkeypatch.setattr(app,'IS_HMONG',True)
    client=TestClient(app.app)
    response=client.get('/help/hmong')
    assert response.status_code==200
    assert '--test-voice' in response.text and 'id="guide-print"' in response.text
    policy=response.headers['content-security-policy']
    assert "'unsafe-inline'" not in policy
    for tag in ('style','script'):
        for block in re.findall('<'+tag+r'\b[^>]*>(.*?)</'+tag+'>',response.text,re.S|re.I):
            expected=base64.b64encode(hashlib.sha256(block.replace('\r\n','\n').encode()).digest()).decode()
            assert 'sha256-'+expected in policy
    assert 'onclick=' not in response.text
    assert 'href="HMONG-NATIVE.md"' not in response.text
    root=client.get('/')
    assert root.headers['content-security-policy'].count('sha256-')==0
    monkeypatch.setattr(app,'IS_HMONG',False)
    assert client.get('/help/hmong').status_code==404
