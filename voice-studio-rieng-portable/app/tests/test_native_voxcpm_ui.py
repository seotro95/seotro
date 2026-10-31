"""Run backend-selection behavior in Node without loading or faking a model."""
from pathlib import Path
import shutil
import subprocess

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / 'static/app.js'
NODE = shutil.which('node')
pytestmark = pytest.mark.skipif(NODE is None, reason='Node is required for UI behavior checks')

DOM = r'''
const assert = require('node:assert/strict');
const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, {
    value: '', textContent: '', hidden: false, disabled: false, options: [],
    classList: {toggle() {}, add() {}, remove() {}},
    replaceChildren(...children) {this.options = children;},
    append(...children) {this.options.push(...children);},
    setAttribute() {}, removeAttribute() {},
  });
  return elements.get(id);
}
global.document = {getElementById: element, createElement: () => element(Symbol()), querySelectorAll: () => []};
global.localStorage = {getItem: () => null, setItem() {}};
'''


def run_javascript(body):
    source = SCRIPT.read_text(encoding='utf-8')
    # Event registration starts the full app. Exercise its real selection
    # functions directly with a tiny DOM; no HTTP/model responses are invented.
    source = source.split("for (const button of document.querySelectorAll('[data-view]')) button.addEventListener", 1)[0]
    result = subprocess.run([NODE, '-'], input=DOM + source + '\n' + body,
                            text=True, capture_output=True, check=False, timeout=15)
    assert result.returncode == 0, result.stderr


def test_native_readiness_requires_the_selected_family_device_and_reference():
    run_javascript(r'''
config = {native_multilingual_ready: true, native_multilingual_cpu_available: true,
 native_multilingual_cuda_available: true, native_voxcpm_ready: true,
 native_voxcpm_cpu_available: true, native_voxcpm_cuda_available: false};
const v = {engine: 'voxcpm', has_sample: true, ready_voxcpm: true, ready_native: true, ready_voxcpm_native: true};
$('international-backend').value = 'voxcpm_native';
$('international-device').value = 'cuda';
assert.equal(voiceReady(v), false);
$('international-device').value = 'cpu';
assert.equal(voiceReady(v), true);
assert.equal(voiceReady({...v, has_sample: false}), false);
assert.equal(voiceReady({...v, ready_voxcpm_native: false}), false);
$('international-backend').value = 'omnivoice';
$('international-device').value = 'cuda';
assert.equal(voiceReady(v), true);
$('international-backend').value = 'voxcpm';
assert.equal(voiceReady(v), true);
''')


def test_native_settings_use_correct_steps_and_keep_backend_device_tuning_separate():
    run_javascript(r'''
config = {native_voxcpm_ready: true, cpu_cores: 8};
$('resource-profile').value = 'smooth';
$('international-backend').value = 'voxcpm_native';
$('international-device').value = 'cuda';
$('international-precision').value = 'int8';
$('voxcpm-steps').value = '10';
$('omnivoice-steps').value = '32';
const v = {engine: 'voxcpm'};
assert.equal(renderTuningKey('voxcpm', 'balanced'), 'smooth:voxcpm:balanced:voxcpm_native:cuda');
assert.equal(internationalSettings().voxcpm_steps, 10);
assert.equal(internationalSettings().international_device, 'cuda');
assert.equal(internationalSettings().international_precision, 'fp32');
assert.equal(renderingPresets(v).fast.voxcpm_steps, 4);
assert.equal(renderingPresets(v).quality.voxcpm_steps, 10);
assert.equal(renderingPresets(v).fast.nano_parallel, 1);
assert.equal(renderingPresets(v).fast.omnivoice_steps, undefined);
$('international-device').value = 'cpu';
assert.equal(renderTuningKey('voxcpm', 'balanced'), 'smooth:voxcpm:balanced:voxcpm_native:cpu');
$('international-backend').value = 'omnivoice';
assert.equal(renderTuningKey('voxcpm', 'balanced'), 'smooth:voxcpm:balanced:omnivoice:cpu');
assert.equal(renderingPresets(v).fast.omnivoice_steps, 8);
assert.equal(renderingPresets(v).quality.omnivoice_steps, 16);
for (const saved of ['voxcpm', 'omnivoice', 'voxcpm_native']) {
 renderPreferences.international_backend = saved;
 assert.equal(initialInternationalBackend(), saved);
}
delete renderPreferences.international_backend;
assert.equal(initialInternationalBackend(), 'voxcpm_native');
config.native_voxcpm_ready = false;
assert.equal(initialInternationalBackend(), 'voxcpm');
''')


def test_gpu_action_preserves_voice_language_editor_steps_and_explicit_selection():
    run_javascript(r'''
config = {native_voxcpm_ready: true, native_voxcpm_cpu_available: true,
 native_voxcpm_cuda_available: true, cpu_cores: 8};
voices = [{id:'selected-ja', name:'Selected sample', engine:'voxcpm', languages:['ja'],
 has_sample:true, ready_voxcpm_native:true}];
renderSettingsInitialized = true;
$('voice').value = 'selected-ja';
$('language').value = 'ja';
$('script').value = '元のスクリプト。';
$('international-backend').value = 'voxcpm';
$('international-device').value = 'cpu';
$('international-precision').value = 'fp32';
$('resource-profile').value = 'smooth';
$('render-mode').value = 'balanced';
$('cpu-execution').value = 'auto';
$('voxcpm-steps').value = '10';
$('nano-parallel').value = '2';
$('nano-threads').value = '4';
$('audio-fit-backend').value = 'ffmpeg';
$('quality').value = 'auto';
updateRenderNote = () => {};
updateVoice = () => {};
renderLibrary = () => {};
chooseNativeVoxCuda();
assert.equal($('voice').value, 'selected-ja');
assert.equal($('language').value, 'ja');
assert.equal($('script').value, '元のスクリプト。');
assert.equal($('voxcpm-steps').value, '10');
assert.equal($('international-backend').value, 'voxcpm_native');
assert.equal($('international-device').value, 'cuda');
assert.equal($('nano-parallel').value, '1');
assert.equal(renderPreferences.international_backend, 'voxcpm_native');
assert.equal(renderPreferences.international_device, 'cuda');
assert.equal(renderPreferences.tuning['smooth:voxcpm:balanced:voxcpm_native:cuda'].voxcpm_steps, 10);
assert.match($('notice').textContent, /xác nhận GPU/);
config.native_voxcpm_cuda_available = false;
$('international-backend').value = 'omnivoice';
$('international-device').value = 'cuda';
chooseNativeVoxCuda();
assert.equal($('international-backend').value, 'omnivoice');
assert.equal($('international-device').value, 'cuda');
assert.match($('notice').textContent, /cài bộ VoxCPM2 native CUDA/);
''')


def test_controls_distinguish_native_voxcpm_steps_from_omnivoice_steps():
    run_javascript(r'''
config = {native_voxcpm_ready: true, native_voxcpm_cpu_available: true,
 native_multilingual_ready: true, native_multilingual_cpu_available: true,
 benchmark_languages:['ja']};
voices = [{id:'selected', name:'Selected sample', engine:'voxcpm', languages:['ja'],
 has_sample:true, ready_voxcpm_native:true, ready_native:true, ready_voxcpm:true}];
$('voice').value = 'selected'; $('language').value = 'ja';
$('international-device').value = 'cpu';
appliedRenderEngine = 'voxcpm';
updateSuggestion = () => {}; updateRenderNote = () => {};
$('international-backend').value = 'voxcpm_native';
updateVoice();
assert.equal($('voxcpm-steps').disabled, false);
assert.equal($('voxcpm-step-field').hidden, false);
assert.equal($('international-precision-field').hidden, true);
assert.equal($('omnivoice-step-field').hidden, true);
assert.equal($('omnivoice-steps').disabled, true);
assert.equal($('international-device').disabled, false);
$('international-backend').value = 'omnivoice';
updateVoice();
assert.equal($('voxcpm-steps').disabled, true);
assert.equal($('voxcpm-step-field').hidden, true);
assert.equal($('omnivoice-step-field').hidden, false);
assert.equal($('omnivoice-steps').disabled, false);
$('international-backend').value = 'voxcpm';
updateVoice();
assert.equal($('international-device').disabled, true);
assert.equal($('international-precision-field').hidden, false);
assert.equal($('voxcpm-steps').disabled, false);
''')
