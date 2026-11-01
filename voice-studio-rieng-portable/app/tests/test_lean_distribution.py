import json
import app
from test_standalone_api import studio  # noqa: F401
from distribution import distribution_profile
from test_native_voxcpm_ui import run_javascript
from test_reference_voices_api import reference_catalog  # noqa: F401


def test_lean_package_profile_and_explicit_cpu_backend(tmp_path):
    (tmp_path/'DISTRIBUTION.json').write_text(json.dumps({'schema':1,'profile':'lean-19-cpu'}))
    assert distribution_profile(tmp_path)=='lean-19-cpu'
    run_javascript(r'''
config={distribution_profile:'lean-19-cpu',native_multilingual_ready:true};
renderPreferences.international_backend='voxcpm_native';
assert.equal(initialInternationalBackend(),'omnivoice');
renderPreferences.international_backend='voxcpm';
assert.equal(initialInternationalBackend(),'omnivoice');
''')


def test_lean_catalog_keeps_private_references_turbo_nano_and_hides_qwen(reference_catalog,monkeypatch):
    client, data, _, _ = reference_catalog
    monkeypatch.setattr(app,'distribution_profile',lambda:'lean-19-cpu')
    monkeypatch.setattr(app,'model_ready',lambda engine:engine in {'vieneu','vieneu_nano'})
    entries=client.get('/api/voices').json()['voices']
    assert len([v for v in entries if v.get('category')=='reference'])==6
    assert len([v for v in entries if v.get('variant')=='turbo_vi_en'])==3
    assert not [v for v in entries if v['engine'] in {'qwen','qwen_clone'}]
    assert [v for v in entries if v['engine']=='vieneu_nano']
    assert [v for v in entries if v['engine']=='vieneu']
