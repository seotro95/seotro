"""Run backend-selection behavior in Node without loading or faking a model."""
from pathlib import Path
from html.parser import HTMLParser
import json
import shutil
import subprocess

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / 'static/app.js'
NODE = shutil.which('node')
pytestmark = pytest.mark.skipif(NODE is None, reason='Node is required for UI behavior checks')

DOM = r'''
'use strict';
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


def test_dual_xeon_uses_budgeted_cpu_parallelism_but_cuda_and_omni_keep_one_model():
    run_javascript(r'''
config = {cpu_cores:56, native_voxcpm_ready:true, native_voxcpm_cpu_available:true,
 native_voxcpm_cuda_available:true, native_multilingual_ready:true,
 native_multilingual_cpu_available:true, benchmark_languages:['ja'],
 native_voxcpm_cpu_limits_by_resource: {
  maximum:{max_workers:7,max_threads:4,cpu_budget:28},
  smooth:{max_workers:6,max_threads:4,cpu_budget:26},
  light:{max_workers:1,max_threads:2,cpu_budget:2}},
 native_voxcpm_cpu_rendering_presets_by_resource: {
  maximum:{fast:{nano_parallel:7,nano_threads:4,voxcpm_steps:4,audio_fit_backend:'wsola'}},
  smooth:{fast:{nano_parallel:6,nano_threads:4,voxcpm_steps:4,audio_fit_backend:'wsola'}},
  light:{fast:{nano_parallel:1,nano_threads:2,voxcpm_steps:4,audio_fit_backend:'wsola'}}}};
voices = [{id:'selected-ja',name:'Selected sample',engine:'voxcpm',languages:['ja'],
 has_sample:true,ready_voxcpm_native:true,ready_native:true}];
$('voice').value='selected-ja'; $('language').value='ja'; $('script').value='元のスクリプト。';
$('international-backend').value='voxcpm_native'; $('international-device').value='cpu';
$('resource-profile').value='maximum'; $('render-mode').value='fast';
$('nano-parallel').options=Array.from({length:32},(_,i)=>({value:String(i+1)}));
updateSuggestion=()=>{}; updateRenderNote=()=>{};
applyRenderMode('fast',{useSaved:false,remember:false});
updateVoice();
assert.equal($('nano-parallel').value,'7');
assert.equal($('nano-threads').value,'4');
assert.equal($('nano-threads').max,'4');
assert.equal($('nano-parallel').disabled,false);
assert.equal($('nano-parallel').options[6].disabled,false);
assert.equal($('nano-parallel').options[7].disabled,true);
rememberRenderTuning();
$('resource-profile').value='smooth';
$('voxcpm-steps').value='10';
applyResourceBudget();
assert.equal($('nano-parallel').value,'6');
assert.equal($('nano-threads').value,'4');
assert.equal($('voxcpm-steps').value,'10');
assert.equal($('voice').value,'selected-ja');
assert.equal($('language').value,'ja');
assert.equal($('script').value,'元のスクリプト。');
$('resource-profile').value='maximum';
applyRenderMode('fast',{remember:false});
assert.equal($('nano-parallel').value,'7');
$('international-device').value='cuda';
applyRenderMode('fast',{remember:false}); updateVoice();
assert.equal($('nano-parallel').value,'1');
assert.equal($('nano-parallel').disabled,true);
assert.equal($('nano-parallel').options[1].disabled,true);
$('international-device').value='cpu';
applyRenderMode('fast',{remember:false}); updateVoice();
assert.equal($('nano-parallel').value,'7');
assert.equal($('nano-parallel').disabled,false);
$('international-backend').value='omnivoice';
applyRenderMode('fast',{remember:false}); updateVoice();
assert.equal($('nano-parallel').value,'1');
assert.equal($('nano-parallel').disabled,true);
''')


def test_native_cpu_manual_resources_cannot_exceed_server_thread_or_ram_budget():
    run_javascript(r'''
config={native_voxcpm_cpu_limits_by_resource:{maximum:{max_workers:8,max_threads:8,cpu_budget:26}}};
$('international-backend').value='voxcpm_native'; $('international-device').value='cpu';
$('resource-profile').value='maximum';
voices=[{id:'selected',engine:'voxcpm'}]; $('voice').value='selected';
$('render-mode').value='fast'; $('nano-parallel').value='8'; $('nano-threads').value='8';
updateRenderNote=()=>{};
rememberRenderTuning();
assert.equal($('nano-parallel').value,'8');
assert.equal($('nano-threads').value,'3');
const saved=renderPreferences.tuning[renderTuningKey('voxcpm','fast')];
assert.equal(saved.nano_parallel*saved.nano_threads,24);
config.native_voxcpm_cpu_limits_by_resource.maximum.max_workers=6;
rememberRenderTuning();
assert.equal($('nano-parallel').value,'6');
''')


def test_hour_proof_is_distinct_from_a_fast_short_sample_and_subtitle_timeline():
    run_javascript(r'''
const sample={spoken_realtime_multiplier:50,estimated_hour_seconds:72,
 measurement_audio_seconds:10,measurement_elapsed_seconds:.2,
 target_30x_met_on_sample:true,actual_hour_of_speech_generated:false,
 target_30x_verified_on_hour_or_longer:false,estimate_only:true};
const short=formatSpeedReport(sample);
assert.match(short,/Mẫu ngắn đạt tốc độ 30×/);
assert.match(short,/chưa xác minh bằng bản tạo đủ 1 giờ/);
assert.doesNotMatch(short,/Đã xác minh tốc độ/);
const full=formatSpeedReport({...sample,measurement_audio_seconds:3600,
 measurement_elapsed_seconds:120,actual_hour_of_speech_generated:true,
 target_30x_verified_on_hour_or_longer:true});
assert.match(full,/đã tạo đủ ít nhất 1 giờ lời đọc thực tế/);
assert.match(full,/Đã xác minh tốc độ từ 30×/);
assert.match(full,/Thời gian quy đổi từ bản thu này/);
assert.doesNotMatch(full,/Ước tính cho bản dài chưa được xác minh/);
const slow=formatSpeedReport({...sample,measurement_audio_seconds:3600,
 measurement_elapsed_seconds:121,actual_hour_of_speech_generated:true,
 target_30x_met_on_sample:false});
assert.match(slow,/Bản tạo đủ 1 giờ lời đọc này chưa xác minh đạt mục tiêu 30×/);
const boundary=formatSpeedReport({...sample,measurement_audio_seconds:3600,
 measurement_elapsed_seconds:120.001,actual_hour_of_speech_generated:true,
 target_30x_verified_on_hour_or_longer:true});
assert.doesNotMatch(boundary,/Đã xác minh tốc độ/);
assert.match(boundary,/120,001 giây xử lý/);
const timeline=formatSpeedReport({...sample,output_timeline_seconds:7200,
 excluded_silence_seconds:7190,actual_hour_of_speech_generated:true,
 target_30x_verified_on_hour_or_longer:true});
assert.doesNotMatch(timeline,/Đã xác minh tốc độ/);
assert.doesNotMatch(timeline,/đã tạo đủ ít nhất 1 giờ/);
assert.match(timeline,/7.190 giây khoảng lặng/);
''')


CUDA_ACTION_SETUP = r'''
config={cpu_cores:56,native_voxcpm_ready:true,native_voxcpm_cpu_available:true,
 native_voxcpm_cuda_available:true,benchmark_languages:['fr','es','ja']};
voices=[{id:'selected-private-reference',name:'Selected reference',engine:'voxcpm',
 languages:['fr','es','ja'],has_sample:true,ready_voxcpm_native:true}];
renderSettingsInitialized=true;
$('voice').value='selected-private-reference';
$('language').value=selectedLanguage;
$('script').value=originalScript;
$('international-backend').value='voxcpm';
$('international-device').value='cpu';
$('international-precision').value='int8';
$('resource-profile').value='maximum'; $('render-mode').value='quality';
$('cpu-execution').value='auto'; $('delivery').value='natural';
$('voxcpm-steps').value='10'; $('omnivoice-steps').value='16';
$('nano-steps').value='8'; $('nano-parallel').value='4'; $('nano-threads').value='7';
$('audio-fit-backend').value='ffmpeg'; $('quality').value='auto';
renderPreferences.tuning['maximum:voxcpm:fast:voxcpm_native:cuda']={voxcpm_steps:10,nano_parallel:1,nano_threads:8};
const requests=[]; const displayed=[];
updateVoice=()=>{}; updateRenderNote=()=>{}; renderLibrary=()=>{};
setOutput=job=>displayed.push(job); refreshHistory=async()=>{};
$('output-heading').scrollIntoView=()=>{};
'''


@pytest.mark.parametrize(('language', 'script'), [
    ('fr', 'Voici mon texte original. Écoutez la voix choisie.'),
    ('es', 'Este es mi texto original. Conserva esta voz.'),
    ('ja', 'これは元の原稿です。同じ声と言語を使います。'),
])
def test_fast_cuda_action_submits_four_steps_in_selected_language_without_changing_script(language, script):
    run_javascript('const selectedLanguage=' + json.dumps(language) + ';\n'
                   + 'const originalScript=' + json.dumps(script) + ';\n'
                   + CUDA_ACTION_SETUP + r'''
post=async(path,payload)=>{requests.push({path,payload}); return {id:'actual-job',status:'queued'};};
(async()=>{
 await chooseNativeVoxCudaFastAndBenchmark();
 assert.equal(requests.length,1);
 const {path,payload}=requests[0];
 assert.equal(path,'/api/benchmark');
 assert.equal(payload.voice_id,'selected-private-reference');
 assert.equal(payload.language,selectedLanguage);
 assert.equal(payload.international_backend,'voxcpm_native');
 assert.equal(payload.international_device,'cuda');
 assert.equal(payload.render_mode,'fast');
 assert.equal(payload.voxcpm_steps,4);
 assert.equal(payload.nano_parallel,1);
 assert.equal(payload.international_precision,'fp32');
 assert.equal($('voice').value,'selected-private-reference');
 assert.equal($('language').value,selectedLanguage);
 assert.equal($('script').value,originalScript);
 assert.equal($('voxcpm-steps').value,'4');
 assert.equal(renderPreferences.tuning['maximum:voxcpm:fast:voxcpm_native:cuda'].voxcpm_steps,4);
 assert.equal(renderPreferences.tuning['maximum:voxcpm:quality:int8'].voxcpm_steps,10);
 assert.equal(renderPreferences.international_backend,'voxcpm_native');
 assert.equal(renderPreferences.international_device,'cuda');
 assert.equal(displayed[0].id,'actual-job');
 assert.equal(displayed[0].status,'queued');
 assert.match($('notice').textContent,/Đang tạo mẫu ngắn/);
 assert.doesNotMatch($('notice').textContent,/Đã xác minh|đạt 30×|GPU đã hoạt động/);
})().catch(error=>{console.error(error);process.exitCode=1;});
''')


@pytest.mark.parametrize('missing', ['reference', 'reference_flag', 'cuda_package', 'sample_language'])
def test_fast_cuda_action_does_not_change_settings_when_prerequisites_are_missing(missing):
    changes = {
        'reference': "voices[0].has_sample=false;",
        'reference_flag': "delete voices[0].has_sample;",
        'cuda_package': "config.native_voxcpm_cuda_available=false;",
        'sample_language': "config.benchmark_languages=['vi'];",
    }
    run_javascript("const selectedLanguage='ja'; const originalScript='元の原稿。';\n"
                   + CUDA_ACTION_SETUP + changes[missing] + r'''
post=async(path,payload)=>{requests.push({path,payload});return {id:'unexpected-job'};};
(async()=>{
 await chooseNativeVoxCudaFastAndBenchmark();
 assert.equal(requests.length,0);
 assert.equal($('international-backend').value,'voxcpm');
 assert.equal($('international-device').value,'cpu');
 assert.equal($('render-mode').value,'quality');
 assert.equal($('voxcpm-steps').value,'10');
 assert.equal($('voice').value,'selected-private-reference');
 assert.equal($('language').value,'ja');
 assert.equal($('script').value,originalScript);
})().catch(error=>{console.error(error);process.exitCode=1;});
''')


def test_fast_cuda_job_error_remains_visible_without_cpu_or_vietnamese_fallback():
    run_javascript("const selectedLanguage='ja'; const originalScript='元の原稿。';\n"
                   + CUDA_ACTION_SETUP + r'''
post=async(path,payload)=>{requests.push({path,payload});throw new Error('CUDA: actual device initialization failed');};
(async()=>{
 await chooseNativeVoxCudaFastAndBenchmark();
 assert.equal(requests.length,1);
 assert.equal(displayed.length,0);
 assert.equal($('international-backend').value,'voxcpm_native');
 assert.equal($('international-device').value,'cuda');
 assert.equal($('language').value,'ja');
 assert.equal($('voice').value,'selected-private-reference');
 assert.equal($('script').value,originalScript);
 assert.equal($('voxcpm-steps').value,'4');
 assert.match($('notice').textContent,/actual device initialization failed/);
 assert.equal(submitting,false);
})().catch(error=>{console.error(error);process.exitCode=1;});
''')


@pytest.mark.parametrize('missing_sample', [False, True])
def test_fast_cuda_accepts_uploaded_french_voice_without_legacy_sample_flag(missing_sample):
    sample_state = 'voices[0].has_sample=false;' if missing_sample else 'delete voices[0].has_sample;'
    run_javascript("const selectedLanguage='fr'; const originalScript='Voici mon texte original. Écoutez cette voix.';\n"
                   + CUDA_ACTION_SETUP + r'''
voices[0].category='cloned'; voices[0].id='uploaded-french';
delete voices[0].ready_voxcpm_native;
$('voice').value='uploaded-french';
''' + sample_state + '\nconst expectedRequests=' + ('0' if missing_sample else '1') + r''';
post=async(path,payload)=>{requests.push({path,payload});return {id:'uploaded-voice-job',status:'queued'};};
(async()=>{
 await chooseNativeVoxCudaFastAndBenchmark();
 assert.equal(requests.length,expectedRequests);
 assert.equal($('voice').value,'uploaded-french');
 assert.equal($('language').value,'fr');
 assert.equal($('script').value,originalScript);
 if(expectedRequests){
  assert.equal(requests[0].payload.voice_id,'uploaded-french');
  assert.equal(requests[0].payload.language,'fr');
  assert.equal(requests[0].payload.international_backend,'voxcpm_native');
  assert.equal(requests[0].payload.international_device,'cuda');
  assert.equal(requests[0].payload.voxcpm_steps,4);
 }else{
  assert.equal($('international-backend').value,'voxcpm');
  assert.equal($('international-device').value,'cpu');
  assert.equal($('voxcpm-steps').value,'10');
 }
})().catch(error=>{console.error(error);process.exitCode=1;});
''')


def test_clean3_html_requests_new_javascript_cache_identity():
    class Scripts(HTMLParser):
        def __init__(self):
            super().__init__()
            self.sources = []

        def handle_starttag(self, tag, attrs):
            if tag == 'script':
                self.sources.append(dict(attrs).get('src'))

    parser = Scripts()
    parser.feed(SCRIPT.with_name('index.html').read_text(encoding='utf-8'))
    assert parser.sources == ['/static/app.js?v=1.12.1-clean3']
