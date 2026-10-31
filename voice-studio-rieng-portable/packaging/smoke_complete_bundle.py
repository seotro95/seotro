"""Exercise the assembled Windows bundle with its own Python and public speech.

All inference is real, offline and CPU-only. Generated jobs, audio and local
transcription caches stay under app/.data and are outside the assembler's
frozen publication inventory. The only exported artifact is the JSON report.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import locale
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
import wave

from smoke_clean_bundle import configure, digest


REFERENCE_SHA256 = '32bf74dfb8342ccc8284f47a9e5fe1f41b458a983a00938ed170f76951ce638f'
PRIVATE_PACK_SHA256 = '1992c607a8ea9f64aa1821c751259698c146743a10b3da5b73f5738816fb7d82'
QWEN_SPEAKERS = {'Ryan', 'Aiden', 'Ono_Anna', 'Sohee', 'Vivian', 'Serena', 'Uncle_Fu', 'Dylan', 'Eric'}
NATIVE_TEXT_POLICY = 'unicode-whitespace+ctype-C-v1'
FORBIDDEN_MAIN_IMPORTS = ('torch', 'transformers', 'qwen_tts', 'faster_whisper', 'ctranslate2', 'av')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def assert_isolated_imports():
    polluted = [name for name in FORBIDDEN_MAIN_IMPORTS
                if any(module == name or module.startswith(name + '.') for module in sys.modules)]
    require(not polluted, 'Optional model libraries entered the main Nano/Turbo process: ' + ', '.join(polluted))


def application_digest(root):
    """Use the same exact application-byte mapping as build_full_update."""
    app = root / 'app'
    paths = [p for p in app.iterdir() if p.is_file() and not p.name.startswith(('.', 'test_'))
             and p.suffix in {'.py', '.ps1'}]
    for directory, directories, names in os.walk(app / 'static'):
        directories[:] = sorted(n for n in directories if not n.startswith('.')
                                and n not in {'__pycache__', 'node_modules', '.git', '.venv', 'venv'})
        paths.extend(Path(directory) / name for name in sorted(names)
                     if not name.startswith('.') and Path(name).suffix.lower() in {'.html', '.css', '.js'})
    records = {p.relative_to(root).as_posix(): digest(p) for p in paths}
    return hashlib.sha256(json.dumps(records, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def check_packaging(root, reference):
    info = json.loads((root / 'BUILD_INFO.json').read_text(encoding='utf-8'))
    require(info.get('version') == '1.12.2' and info.get('package_type') == 'windows-x64-portable-complete',
            'Expected the assembled complete Windows application 1.12.2')
    app_sha = application_digest(root)
    require(app_sha == info.get('application_source_sha256'), 'Actual bundled application bytes differ from BUILD_INFO')
    for name in ('runtime/python.exe', 'runtime-qwen/python.exe', 'runtime-qwen/VOICE-STUDIO-QWEN.json',
                 'runtime-native/cpu/audiocpp.dll', 'runtime-native/cuda/audiocpp.dll',
                 'ffmpeg/bin/ffmpeg.exe', 'ffmpeg/bin/ffprobe.exe', 'CAI_19_GIONG.bat',
                 'install_secure_voices.ps1', 'MO_TOOL.bat', 'EXTRA-MODEL-CPU-QA.json',
                 'app/.data/models/vieneu_nano.ready', 'app/.data/models/vieneu.ready',
                 'app/.data/models/voxcpm-native.ready', 'app/.data/models/omnivoice.ready',
                 'app/.data/models/qwen.ready', 'app/.data/models/qwen_clone.ready',
                 'app/.data/models/native-asr/VOICE-STUDIO-ASR.json'):
        require((root / name).is_file(), 'Missing complete-bundle asset: ' + name)
    manifest = json.loads((root / 'delivery/manifest.json').read_text(encoding='utf-8-sig'))
    require(manifest.get('format') == 'voice-studio-private-delivery-v1'
            and manifest.get('encrypted_file') == 'voices.vspack'
            and manifest.get('encrypted_sha256') == PRIVATE_PACK_SHA256,
            'The original encrypted voice manifest was replaced')
    encrypted = root / 'delivery/voices.vspack'
    require(encrypted.stat().st_size == manifest.get('encrypted_size') == 6544320
            and digest(encrypted) == PRIVATE_PACK_SHA256, 'The original encrypted voice pack changed')
    require(reference.is_file() and digest(reference) == REFERENCE_SHA256,
            'Use only the pinned public audio.cpp assets/resources/b.wav reference')
    with wave.open(str(reference)) as source:
        duration = source.getnframes() / source.getframerate()
        require(source.getcomptype() == 'NONE' and 14 <= duration <= 14.2,
                'The pinned public reference is not the expected approximately 14.07-second PCM')
    return {'application_source_sha256': app_sha, 'application_source_commit': info.get('application_source_commit'),
            'encrypted_private_pack_preserved': True, 'encrypted_private_pack_sha256': PRIVATE_PACK_SHA256,
            'private_voice_unlock_attempted': False, 'private_recordings_used': False,
            'public_reference_sha256': REFERENCE_SHA256, 'public_reference_seconds': duration}


def pcm(path, np, sf):
    audio, rate = sf.read(path, dtype='float32')
    require(rate == 24000 and audio.ndim == 1 and len(audio) >= rate * .2,
            'Synthesis did not produce mono 24 kHz PCM: ' + path.name)
    require(np.isfinite(audio).all() and np.max(np.abs(audio)) > .0001,
            'Synthesis produced invalid or silent PCM: ' + path.name)
    return audio, rate


def check_native_execution(execution, family):
    expected = 'voxcpm_native' if family == 'voxcpm2' else 'omnivoice'
    require(execution.get('backend') == expected and execution.get('device') == 'cpu'
            and execution.get('native_text_handling') == NATIVE_TEXT_POLICY,
            'The isolated native process did not confirm CPU and the Unicode/C-locale text policy')
    if family == 'voxcpm2':
        require(execution.get('model_family') == family and execution.get('voxcpm_steps') == 4,
                'The isolated native process did not confirm VoxCPM2 and four steps')
    else:
        require(execution.get('omnivoice_steps') == 8, 'The isolated OmniVoice process did not confirm eight steps')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--reference', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    require(not args.output.exists(), 'Choose a new final Windows QA report path')
    root, reference = args.root.resolve(), args.reference.resolve()
    runtime, data = configure(root)
    os.environ.pop('VOICE_STUDIO_QWEN_PYTHON', None)
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    package = check_packaging(root, reference)
    import numpy as np
    import onnxruntime
    import soundfile as sf
    import httpx
    import psutil
    from fastapi.testclient import TestClient
    import app as studio
    import worker
    import fast_multilingual
    import qwen_backend
    from subtitles import parse_srt
    require(Path(studio.__file__).resolve() == root / 'app/app.py' and studio.DATA == data,
            'The check imported a different application or data directory')
    require(qwen_backend.runtime_python().resolve() == root / 'runtime-qwen/python.exe',
            'The Qwen adapter selected a runtime outside the complete bundle')
    for module in (np, onnxruntime, sf, httpx, psutil):
        require(runtime in Path(module.__file__).resolve().parents,
                'Dependency escaped bundled Python: ' + module.__name__)
    for binary in ('ffmpeg', 'ffprobe'):
        located = shutil.which(binary)
        require(located is not None and Path(located).resolve().parent == root / 'ffmpeg/bin',
                'Audio binary escaped bundled FFmpeg: ' + binary)
        subprocess.run([located, '-version'], check=True, stdout=subprocess.DEVNULL, timeout=30)
    subprocess.run([sys.executable, '-s', '-m', 'pip', 'check'], check=True, timeout=120)
    assert_isolated_imports()
    qa_audio = data / 'qa-audio' / ('complete-' + uuid.uuid4().hex)
    qa_audio.mkdir(parents=True)
    requests, qwen_pids = [], []
    public_text = 'Xin chào. Đây là bản kiểm tra giọng nói tiếng Việt.'
    base = {'language': 'vi', 'quality': 'standard', 'speed': 1, 'nano_steps': 8,
            'nano_threads': 2, 'nano_parallel': 1, 'paragraph_pause': 0,
            'model_memory': 'shared', 'resource_profile': 'maximum',
            'input_format': 'txt', 'text': public_text, 'format': 'wav',
            'render_mode': 'balanced', 'audio_fit_backend': 'wsola', 'delivery': 'natural'}
    srt = ('1\n00:00:00,250 --> 00:00:02,000\nXin chào.\n\n'
           '2\n00:00:02,500 --> 00:00:04,750\nCảm ơn.\n')
    caller_ctype = locale.setlocale(locale.LC_CTYPE)
    phase = 'UI and readiness'
    try:
        with TestClient(studio.app) as client:
            response = client.get('/api/config')
            require(response.status_code == 200, 'Application configuration request failed')
            config = response.json()
            require(config.get('version') == '1.12.2' and config.get('edition') == 'standalone-voice',
                    'The API does not identify complete application 1.12.2')
            required_flags = ('nano_ready', 'native_voxcpm_ready', 'native_voxcpm_cpu_available',
                              'native_multilingual_ready', 'native_multilingual_cpu_available',
                              'native_reference_transcription_ready')
            require(all(config.get(key) is True for key in required_flags),
                    'The full application did not report all bundled native/ASR engines ready')
            require(all(config.get('models', {}).get(key) is True for key in ('vieneu', 'qwen', 'qwen_clone')),
                    'The full application did not report Turbo and both Qwen models ready')
            for url, expected in (('/', None), ('/static/app.js', root / 'app/static/app.js'),
                                  ('/static/style.css', root / 'app/static/style.css')):
                result = client.get(url)
                require(result.status_code == 200 and (expected is None or result.content == expected.read_bytes()),
                        'The UI does not match the complete bundle: ' + url)
            response = client.get('/api/voices')
            require(response.status_code == 200, 'Voice catalog request failed')
            voices = response.json()['voices']
            ready_qwen = {v.get('speaker') for v in voices if v.get('engine') == 'qwen' and v.get('ready') is True}
            require(ready_qwen == QWEN_SPEAKERS, 'The actual UI catalog does not mark all nine Qwen presets ready')
            require(all(any(v.get('engine') == engine and v.get('ready') for v in voices)
                        for engine in ('vieneu_nano', 'vieneu')), 'Public Nano/Turbo voices are not ready')
            response = client.get('/api/system-info?quick=true')
            require(response.status_code == 200 and response.json().get('physical_cores', 0) >= 1
                    and response.json().get('ram_gb'), 'Hardware detection failed')
            response = client.post('/api/scripts/convert', json={
                'text': public_text, 'input_format': 'txt', 'output_format': 'txt'})
            require(response.status_code == 200 and response.json().get('text') == public_text,
                    'The TXT converter changed the public input')
            assert_isolated_imports()

            def run_job(job):
                print('Actual complete-bundle request: ' + job['engine'] + ' / ' + job['language'], flush=True)
                started = time.perf_counter()
                worker.render(job)
                elapsed = time.perf_counter() - started
                output = data / 'audio' / (job['id'] + '.' + job['format'])
                decoded = output
                if job['format'] == 'mp3':
                    decoded = data / 'parts' / job['id'] / 'decoded-mp3.wav'
                    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(output),
                                    '-ac', '1', '-ar', '24000', '-codec:a', 'pcm_s16le', str(decoded)],
                                   check=True, timeout=60)
                samples, rate = pcm(decoded, np, sf)
                parsed = parse_srt((data / 'audio' / (job['id'] + '.srt')).read_text(encoding='utf-8'))
                if job['input_format'] == 'srt':
                    require(parsed == parse_srt(srt) and len(samples) == round(4.75 * rate)
                            and not np.any(samples[:round(.25 * rate)]), 'Nano SRT output changed the two subtitle clocks')
                    alignment = json.loads((data / 'parts' / job['id'] / 'alignment.json').read_text(encoding='utf-8'))
                    require(alignment.get('sync_ok') and len(alignment.get('cues', [])) == 2,
                            'Nano SRT alignment did not cover both cues')
                studio.write_json(data / 'jobs' / (job['id'] + '.json'), {**job, 'status': 'done'})
                expected_txt = '\n'.join(c['text'] for c in parsed) if job['input_format'] == 'srt' else job['text']
                txt, subtitles, audio = (client.get('/api/jobs/' + job['id'] + '/script.txt'),
                                         client.get('/api/jobs/' + job['id'] + '/script.srt'),
                                         client.get('/api/audio/' + job['id']))
                require(txt.status_code == 200 and txt.text == expected_txt, 'Synthesized TXT export mismatch')
                require(subtitles.status_code == 200 and parse_srt(subtitles.text) == parsed,
                        'Synthesized SRT export mismatch')
                require(audio.status_code == 200 and hashlib.sha256(audio.content).hexdigest() == digest(output),
                        'Synthesized audio export mismatch')
                execution = json.loads((data / 'parts' / job['id'] / 'result.json').read_text(encoding='utf-8'))['execution_settings']
                record = {'engine': job['engine'], 'language': job['language'], 'text': job['text'],
                          'speaker': job['speaker'], 'input_format': job['input_format'], 'output_format': job['format'],
                          'audio_seconds': len(samples) / rate, 'processing_seconds': round(elapsed, 3),
                          'audio_sha256': digest(output), 'valid_pcm': True, 'txt_srt_audio_exports_passed': True,
                          'two_subtitle_clocks_preserved': job['input_format'] == 'srt', 'execution': execution}
                requests.append(record)
                assert_isolated_imports()
                return execution

            phase = 'public Nano/Turbo and subtitles'
            for job in (dict(base, id=uuid.uuid4().hex, engine='vieneu_nano', voice_id='nano-minhquan', speaker='Minh Quân'),
                        dict(base, id=uuid.uuid4().hex, engine='vieneu', voice_id='vi-maianh', speaker='Mai Anh', format='mp3'),
                        dict(base, id=uuid.uuid4().hex, engine='vieneu_nano', voice_id='nano-minhquan', speaker='Minh Quân',
                             text=srt, input_format='srt', cue_fit='auto', max_cue_tempo=1.5)):
                run_job(job)
            worker.reset_nano_models()
            gc.collect()
            phase = 'isolated Qwen through actual worker'
            for speaker, voice_id, language, text in (('Ryan', 'qw-ryan', 'en-US', 'Hello.'),
                                                      ('Ono_Anna', 'qw-ono', 'ja', 'はい。'),
                                                      ('Sohee', 'qw-sohee', 'ko', '안녕.')):
                job = dict(base, id=uuid.uuid4().hex, engine='qwen', voice_id=voice_id, speaker=speaker,
                           language=language, text=text, nano_threads=4, model_memory='process')
                execution = run_job(job)
                require(execution.get('backend') == 'qwen_isolated' and execution.get('device') == 'cpu'
                        and execution.get('precision') == 'fp32', 'The actual worker did not confirm isolated Qwen CPU FP32')
                qwen_pids.append(qwen_backend._client.process.pid)
            require(len(set(qwen_pids)) == 1, 'The three Qwen presets did not reuse one warm model child')
            worker.reset_nano_models()
            require(qwen_backend.execution_info() == {}, 'The Qwen child remained active before native model loading')

        phase = 'OmniVoice with blank transcript and isolated local ASR'
        cache = data / 'cache/native-transcripts'
        cached_before = {p.name for p in cache.glob('*.json')}
        # Exercise a non-C caller without changing the isolated child's policy.
        # The runtime metadata below confirms the child's C-locale text policy.
        locale.setlocale(locale.LC_CTYPE, '.1252')
        native_caller_locale = locale.setlocale(locale.LC_CTYPE)
        started = time.perf_counter()
        omni = fast_multilingual.create_synthesizer(reference, data, threads=4, steps=8, device='cpu',
                                                   language='ko', reference_text='', reference_language='en-US')
        output = qa_audio / 'omni-ko.wav'
        omni('안녕하세요.', output)
        elapsed = time.perf_counter() - started
        audio, rate = pcm(output, np, sf)
        execution = fast_multilingual.execution_info()
        check_native_execution(execution, 'omnivoice')
        recognized = []
        for path in cache.glob('*.json'):
            record = json.loads(path.read_text(encoding='utf-8'))
            if record.get('reference_sha256') == REFERENCE_SHA256 and record.get('language') == 'en':
                require(path.name not in cached_before and record.get('schema') == 1
                        and record.get('source') == 'local_machine_transcription' and record.get('local_only') is True
                        and isinstance(record.get('text'), str) and len(record['text'].split()) >= 5,
                        'Blank-transcript OmniVoice did not create a new local-ASR reference cache')
                recognized.append(record['text'])
        require(len(recognized) == 1, 'The actual blank-transcript route did not produce one matching ASR record')
        from native_transcript import reference_transcript
        before = {p.name: (p.stat().st_mtime_ns, p.read_bytes()) for p in cache.glob('*.json')}
        require(reference_transcript(reference, data, 'en-US') == recognized[0], 'ASR cache returned different text')
        require(before == {p.name: (p.stat().st_mtime_ns, p.read_bytes()) for p in cache.glob('*.json')},
                'Repeated reference transcription rewrote its verified cache')
        requests.append({'engine': 'omnivoice', 'language': 'ko', 'text': '안녕하세요.', 'steps': 8,
                         'reference_text_supplied': False, 'actual_local_asr_cache_created': True,
                         'persistent_asr_cache_reused': True, 'asr_text_sha256': hashlib.sha256(recognized[0].encode()).hexdigest(),
                         'valid_pcm': True, 'audio_seconds': len(audio) / rate,
                         'processing_seconds': round(elapsed, 3), 'audio_sha256': digest(output), 'execution': execution})
        assert_isolated_imports()
        worker.close_international_backends()
        require(fast_multilingual.execution_info() == {}, 'OmniVoice child remained active before VoxCPM2 loading')
        phase = 'VoxCPM2 Unicode stdio-child regression'
        for index, (language, text) in enumerate((
            ('ko', '선택한 목소리의 속도를 측정하기 위해 짧은 글을 읽습니다.'),
            ('zh', '你好。'), ('es', 'Hola. Esta es una prueba de voz.'), ('ja', 'こんにちは。これは音声のテストです。'))):
            print('Actual complete-bundle native request: voxcpm2 / ' + language, flush=True)
            synthesize = fast_multilingual.create_synthesizer(reference, data, threads=4, steps=4,
                                                             device='cpu', language=language, family='voxcpm2')
            output = qa_audio / f'voxcpm-{index}-{language}.wav'
            started = time.perf_counter()
            synthesize(text, output)
            elapsed = time.perf_counter() - started
            audio, rate = pcm(output, np, sf)
            execution = fast_multilingual.execution_info()
            check_native_execution(execution, 'voxcpm2')
            require(locale.setlocale(locale.LC_CTYPE) == native_caller_locale,
                    'The isolated native session modified the main caller character locale')
            requests.append({'engine': 'voxcpm_native', 'language': language, 'text': text, 'steps': 4,
                             'valid_pcm': True, 'audio_seconds': len(audio) / rate,
                             'processing_seconds': round(elapsed, 3), 'audio_sha256': digest(output), 'execution': execution})
            assert_isolated_imports()
        phase = 'VoxCPM2 full thirty-second public reference'
        public_samples, public_rate = sf.read(reference, dtype='float32')
        require(public_samples.ndim == 1, 'Expected the pinned mono public reference')
        long_samples = np.tile(public_samples, 3)[:30 * public_rate]
        require(len(long_samples) == 30 * public_rate, 'The public reference fixture is not thirty seconds')
        long_reference = qa_audio / 'public-reference-thirty-seconds.wav'
        sf.write(long_reference, long_samples, public_rate, subtype='PCM_16')
        long_reference_sha = digest(long_reference)
        synthesize = fast_multilingual.create_synthesizer(long_reference, data, threads=4, steps=4,
                                                         device='cpu', language='zh', family='voxcpm2')
        output = qa_audio / 'voxcpm-thirty-second-reference.wav'
        started = time.perf_counter()
        synthesize('你好。', output)
        elapsed = time.perf_counter() - started
        audio, rate = pcm(output, np, sf)
        execution = fast_multilingual.execution_info()
        check_native_execution(execution, 'voxcpm2')
        require(execution.get('voxcpm_reference_encoder_capacity') == 481280,
                'The native encoder did not reserve the aligned full thirty-second reference capacity')
        require(digest(long_reference) == long_reference_sha and sf.info(long_reference).duration == 30,
                'The full reference audio was changed or shortened')
        requests.append({'engine': 'voxcpm_native', 'language': 'zh', 'text': '你好。', 'steps': 4,
                         'reference_seconds': 30, 'reference_audio_preserved': True,
                         'reference_created_from_pinned_public_audio': True,
                         'valid_pcm': True, 'audio_seconds': len(audio) / rate,
                         'processing_seconds': round(elapsed, 3), 'audio_sha256': digest(output), 'execution': execution})
        assert_isolated_imports()
        worker.close_international_backends()
        report = {'format': 'voice-studio-complete-windows-smoke-v1', 'platform': sys.platform,
                  'product_version': '1.12.2', 'source_commit': os.environ.get('GITHUB_SHA'), **package,
                  'bundled_python_relocated': True, 'bundled_dependencies_imported': True,
                  'pip_check_passed': True, 'bundled_ffmpeg_and_ffprobe_passed': True,
                  'app_http_smoke_passed': True, 'ui_assets_match_extracted_package': True,
                  'all_bundled_model_readiness_flags_passed': True,
                  'nine_qwen_presets_reported_ready': sorted(ready_qwen),
                  'public_nano_turbo_real_synthesis_passed': True, 'nano_two_cue_srt_clock_and_exports_passed': True,
                  'qwen_worker_synthesis_cpu_fp32_passed': True, 'qwen_one_warm_child_for_three_presets': True,
                  'qwen_all_nine_preset_inference_repeated_here': False,
                  'qwen_base_clone_inference_repeated_here': False,
                  'omnivoice_blank_transcript_local_asr_and_cpu_synthesis_passed': True,
                  'voxcpm2_four_language_stdio_child_cpu_synthesis_passed': True,
                  'voxcpm2_thirty_second_public_reference_preserved_and_synthesized': True,
                  'native_text_handling': NATIVE_TEXT_POLICY, 'native_main_caller_lc_ctype_tested': native_caller_locale,
                  'optional_model_libraries_isolated_from_main': True, 'requests': requests,
                  'gpu_inference_tested': False, 'gtx1060_tested': False, 'full_hour_generated': False,
                  'target_30x_guaranteed': False, 'human_pronunciation_reviewed': False,
                  'private_voice_identity_or_count_independently_verified': False,
                  'generated_audio_or_job_history_exported': False}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8', newline='\n') as destination:
            json.dump(report, destination, ensure_ascii=False, indent=2)
            destination.write('\n')
        print(json.dumps(report, ensure_ascii=False), flush=True)
    except BaseException as error:
        print('Complete Windows smoke failed during ' + phase + ': ' + str(error), flush=True)
        raise
    finally:
        worker.reset_nano_models()
        locale.setlocale(locale.LC_CTYPE, caller_ctype)


if __name__ == '__main__':
    main()
