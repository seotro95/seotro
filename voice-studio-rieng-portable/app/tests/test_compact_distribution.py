import json

import pytest

import app
from distribution import distribution_profile
from test_reference_voices_api import reference_catalog  # noqa: F401
from test_standalone_api import studio  # noqa: F401
from test_native_voxcpm_ui import run_javascript


@pytest.mark.parametrize('record', [None, [], True, {'schema': True, 'profile': 'compact-19'},
                                  {'schema': 1, 'profile': 'unknown'}])
def test_unknown_profiles_do_not_change_existing_installations(tmp_path, record):
    (tmp_path/'DISTRIBUTION.json').write_text(json.dumps(record))
    assert distribution_profile(tmp_path) == 'standard'


def test_explicit_compact_profile_and_missing_record(tmp_path):
    assert distribution_profile(tmp_path) == 'standard'
    (tmp_path/'DISTRIBUTION.json').write_text('{"schema":1,"profile":"compact-19"}')
    assert distribution_profile(tmp_path) == 'compact-19'


@pytest.mark.parametrize('qwen_ready', [False, True])
def test_compact_only_filters_uninstalled_public_qwen_presets(reference_catalog, monkeypatch, qwen_ready):
    client, data, _, _ = reference_catalog
    monkeypatch.setattr(app, 'distribution_profile', lambda: 'compact-19')
    monkeypatch.setattr(app, 'model_ready', lambda engine: engine == 'qwen' and qwen_ready)
    rows = client.get('/api/voices').json()['voices']
    assert len([v for v in rows if v['engine'] == 'qwen']) == (9 if qwen_ready else 0)
    from voice_library import turbo_variant_id
    originals = {'a'*32, 'b'*32, 'c'*32}
    assert {v['id'] for v in rows if v.get('category') == 'reference'} == originals | {turbo_variant_id(v) for v in originals}
    assert client.get('/api/config').json()['default_resource_profile'] == 'maximum'


def test_compact_startup_preserves_saved_profile_over_the_package_default():
    # Exercise the same conditional used by refreshVoices, with the real source.
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1]/'static/app.js').read_text()
    start = source.index("$('resource-profile').value = resourceProfiles.has(renderPreferences.resource_profile)")
    selection = source[start:source.index(';', start)+1]
    run_javascript("config = {default_resource_profile:'maximum'};\n" + selection + "\n"
                   "assert.equal($('resource-profile').value, 'maximum');\n"
                   "renderPreferences.resource_profile = 'light';\n" + selection + "\n"
                   "assert.equal($('resource-profile').value, 'light');")
