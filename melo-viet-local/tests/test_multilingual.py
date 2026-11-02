import hashlib,json
from pathlib import Path
import pytest
import app,local_models,multilingual_backend as multi,pack_install

def test_real_multilingual_presets_and_routes_keep_saved_voices():
    assert len(multi.LANGUAGES)==31
    for code in multi.LANGUAGES:
        voices=multi.voices_for(code)
        assert len(voices)==10 and len({v['id'] for v in voices})==10
        assert [v['gender'] for v in voices]==['Female']*5+['Male']*5
        assert app.backend_for({'op':'voices','engine':'local','language':code,'local_provider':'multi'})=='multi'
    assert not multi.voices_for('ZH') and not multi.voices_for('NO') and not multi.voices_for('MWW')
    for ident,expected in [('supertonic:5','multi'),('piper:vi_VN-vais1000-medium:0','piper'),('Adam','viet')]:
        assert app.backend_for({'op':'render','engine':'local','language':'VI','voice':ident,'local_provider':'multi'})==expected

def test_optional_pack_validates_all_before_copy_and_keeps_existing(tmp_path,monkeypatch):
    source=tmp_path/'source';root=tmp_path/'installed';root.mkdir();(root/'recording.wav').write_bytes(b'keep')
    pack=source/'voice-pack';folder=pack/'models/native';folder.mkdir(parents=True);(folder/'model').write_bytes(b'correct')
    record={'files':{'model':hashlib.sha256(b'correct').hexdigest()}}
    monkeypatch.setattr(pack_install,'multi_catalog',lambda:{'native':record});monkeypatch.setattr(pack_install,'piper_catalog',lambda:[])
    (pack/'PACK.json').write_text(json.dumps({'piper':[],'multi':['native']}))
    pack_install.install(source,root);assert (root/'models/native/model').read_bytes()==b'correct'
    (folder/'model').write_bytes(b'broken')
    with pytest.raises(ValueError):pack_install.install(source,root)
    assert (root/'models/native/model').read_bytes()==b'correct' and (root/'recording.wav').read_bytes()==b'keep'
    (pack/'PACK.json').write_text(json.dumps({'piper':[],'multi':['../escape']}))
    with pytest.raises(ValueError):pack_install.install(source,root)

def test_native_offline_missing_model_fails_without_network(tmp_path,monkeypatch):
    monkeypatch.setenv('MELO_VIET_ROOT',str(tmp_path))
    with pytest.raises(ValueError,match='Chưa có đủ mô hình'):local_models.ensure('supertonic3',True)


def test_hmong_uses_native_reader_without_claiming_verified_dialect_or_gender():
    import hmong_backend
    voice=hmong_backend.voices_for()[0]
    assert voice['gender']=='Unknown' and 'chưa xác minh' in voice['name']
    for provider in ['original','fast','multi']:
        assert app.backend_for({'op':'voices','engine':'local','language':'HMN','local_provider':provider})=='hmong'
        assert app.backend_for({'op':'render','engine':'local','language':'HMN','voice':hmong_backend.VOICE,'local_provider':provider})=='hmong'
