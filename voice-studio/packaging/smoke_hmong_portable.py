"""Exercise the relocated Windows bundle with real offline native/F5 speech.

Run only on a fresh builder-owned directory. This script creates QA jobs but
never deletes personal data; the builder removes its own QA directory afterward.
"""
from __future__ import annotations

import io
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
import urllib.request


PRONUNCIATION_TEST_WORDS = ['ua', 'thaj', 'qab', 'faib', 'rov', 'ris']
PLAIN_SAMPLE = ('Peb ua hauj lwm hauv thaj chaw no. Nyob qab roob. Peb faib mov. '
                'Kuv rov los tsev. Nws hnav ris.')
EXPRESSIVE_SAMPLE = ('[emotion=warm]**Peb ua hauj lwm hauv thaj chaw no.**[pause=0.25]'
                     '[emotion=serious]Nyob qab roob. Peb faib mov. Kuv rov los tsev. Nws hnav ris.')
GENERATED_PREVIEW_FILES = {'hmong-female': 'Hmong-female-2-preview.mp3',
                           'hmong-male': 'Hmong-male-2-preview.mp3'}


def check_batch_entrypoints(root):
    """Exercise the files users double-click through the real Windows shell."""
    root = Path(root)
    entries = [('MO_VOICE_STUDIO_HMONG.bat', '--check')]
    for prefix in ('', 'voice-studio-hmong/'):
        entries.extend((prefix + name, '--check') for name in ('start.bat', 'start_hmong.bat'))
        entries.extend((prefix + name, '--setup-only') for name in ('install.bat', 'install_hmong.bat'))
        # Supplying --check must forward the offline CPU check, never install
        # or download the optional CUDA environment during the native build.
        entries.append((prefix + 'install_hmong_cuda.bat', '--check'))
    entries.append(('MO_HMONG_NHANH.bat', '--check'))
    results = {}
    shell = os.environ.get('COMSPEC', 'cmd.exe')
    for relative, flag in entries:
        batch = root / relative
        print('Native cmd.exe entrypoint:', relative, flag, flush=True)
        # The working directory itself contains spaces after relocation. The
        # ASCII basename avoids cmd's special handling of a quoted /c command.
        backend = 'native' if relative == 'MO_HMONG_NHANH.bat' else 'f5'
        environment = dict(os.environ, HMOOB_BACKEND=backend)
        completed = subprocess.run([shell, '/d', '/c', batch.name, flag], cwd=batch.parent, env=environment,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace', timeout=180)
        print(completed.stdout, end='', flush=True)
        if completed.returncode or 'PASS:' not in completed.stdout:
            raise RuntimeError(f'Batch entrypoint failed: {relative} {flag}, exit {completed.returncode}')
        results[relative] = {'argument': flag, 'exit_code': completed.returncode,
                             'model_download_required': False,
                             'engine': 'hmong_native' if backend == 'native' else 'f5_hmong'}
    return results


def check_source_reference(personal, metadata, gender, *, engine='f5_hmong'):
    """Known source clones must use the current manifest, even for short MP3s."""
    assert personal['engine'] == engine
    assert personal['automatic_reference'] is True
    assert personal['known_preset'] == 'hmong-' + gender
    assert personal['source_sha256'] == metadata['sha256']
    assert abs(personal['source_duration'] - metadata['duration']) < .15, 'Wrong source duration'
    assert personal['transcript'] == metadata['reference']['text']
    assert abs(personal['reference_start'] - metadata['reference']['start']) < .01
    assert abs(personal['reference_end'] - metadata['reference']['end']) < .01
    reference_seconds = metadata['reference']['end'] - metadata['reference']['start']
    assert 3 <= personal['duration'] <= 8.001
    assert abs(personal['duration'] - reference_seconds) < .05, 'Wrong reference duration'


def check_spoken_speed(job):
    """Inserted silence must not increase the measured speech throughput."""
    audio, spoken, silence = (job[key] for key in (
        'audio_seconds', 'spoken_audio_seconds', 'inserted_silence_seconds'))
    assert all(isinstance(value, (int, float)) and not isinstance(value, bool)
               and math.isfinite(value) for value in (audio, spoken, silence))
    assert 0 < spoken <= audio and silence >= 0
    assert abs(spoken + silence - audio) <= 2 / 24000
    report = job['speed_report']
    assert report['measurement_basis'] == 'speech_chunks_excluding_inserted_silence'
    assert abs(report['measurement_audio_seconds'] - spoken) <= .011
    assert abs(report['measurement_output_audio_seconds'] - audio) <= .011
    assert abs(report['measurement_inserted_silence_seconds'] - silence) <= .011
    assert report['measurement_elapsed_seconds'] > 0
    assert abs(report['measurement_elapsed_seconds'] - job['wall_processing_seconds']) <= .002
    assert abs(report['realtime_multiplier'] - spoken / job['wall_processing_seconds']) <= .02
    assert report['target_30x_verified_one_hour'] is False and report['estimate_only'] is True
    return report


def export_generated_preview(client, job, reports):
    """Export an already completed preset job, without requesting new speech."""
    filename = GENERATED_PREVIEW_FILES[job['voice_id']]
    response = client.get('/api/jobs/' + job['id'] + '/export.mp3')
    assert response.status_code == 200 and len(response.content) > 1000, 'Generated MP3 export is missing'
    assert response.headers.get('content-type', '').split(';')[0] == 'audio/mpeg'
    reports = Path(reports)
    reports.mkdir(parents=True, exist_ok=True)
    destination = reports / filename
    destination.write_bytes(response.content)
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
        'stream=codec_name:format=duration', '-of', 'json', str(destination)], timeout=30))
    assert any(stream.get('codec_name') == 'mp3' for stream in probe.get('streams', []))
    assert float(probe['format']['duration']) > 1 / 3
    return {'filename': filename, 'sha256': hashlib.sha256(response.content).hexdigest(),
            'bytes': len(response.content), 'generated': True, 'original_source_recording': False,
            'job_id': job['id'], 'voice_id': job['voice_id'], 'text': job['text'],
            'audio_seconds': job['audio_seconds'],
            'spoken_audio_seconds': job['spoken_audio_seconds'],
            'inserted_silence_seconds': job['inserted_silence_seconds'],
            'speed_report': job['speed_report'],
            'pronunciation_test_words': PRONUNCIATION_TEST_WORDS,
            'pronunciation_evaluated': False, 'target_30x_verified': False,
            'settings': {key: job[key] for key in ('engine', 'hmong_backend', 'hmong_steps',
                'hmong_precision', 'hmong_device', 'delivery',
                'emotion', 'emotion_strength', 'auto_rhythm', 'hmong_phrase_context')},
            'expression': job.get('expression')}


def main():
    assert os.name == 'nt', 'This validation must run on native Windows'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('reports', type=Path)
    parser.add_argument('--backend', choices=('native', 'f5'), default='native')
    args = parser.parse_args()
    root, reports = args.root.resolve(), args.reports.resolve()
    os.environ['HMOOB_BACKEND'] = args.backend
    engine = 'hmong_native' if args.backend == 'native' else 'f5_hmong'
    app_root = root / 'voice-studio-hmong'
    assert Path(sys.executable).resolve().parent == root / 'runtime', 'Use the packaged interpreter'
    assert Path(sys.prefix).resolve() == root / 'runtime', 'Interpreter did not relocate'
    sys.path.insert(0, str(app_root))
    import numpy as np
    import soundfile as sf
    import httpx
    from fastapi.testclient import TestClient
    for module in (np, sf, httpx):
        assert (root / 'runtime') in Path(module.__file__).resolve().parents, 'Dependency escaped bundled runtime'
    import app as studio
    from hmong_assets import references
    voice_metadata = references()
    for gender in ('female', 'male'):
        assert voice_metadata[gender]['reference_text_verified'] is True
        assert voice_metadata[gender]['reference_text_source'] == 'user_provided_for_selected_excerpt'
    for binary in ('ffmpeg', 'ffprobe'):
        subprocess.run([binary, '-version'], check=True, stdout=subprocess.DEVNULL)
    results = {'success': False, 'platform': sys.platform, 'engine': engine,
               'hmong_backend': 'vits_openvoice_v2' if args.backend == 'native' else 'f5',
               'voices': {}, 'clone': False,
               'full_source_previews': {}, 'source_clones': {}, 'manual_crop': False,
               'txt_srt': False, 'mp3': False, 'fast_launcher': False, 'batch_entrypoints': {},
               'expression': {}, 'generated_auditions': {},
               'pronunciation_test_words': PRONUNCIATION_TEST_WORDS,
               'target_30x_verified': False, 'cuda_installer_included': True,
               'cuda_inference_validated': False, 'cuda_installation_exercised': False,
               'speed_measurement_basis': 'speech_chunks_excluding_inserted_silence',
               'native_windows_validation': os.name == 'nt'}
    text = PLAIN_SAMPLE

    def render(client, payload):
        response = client.post('/api/speech', json=payload)
        assert response.status_code == 202, response.text
        job = response.json()
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            response = client.get('/api/jobs/' + job['id'])
            assert response.status_code == 200, response.text
            job = response.json()
            if job['status'] not in {'queued', 'running', 'cancelling'}:
                break
            time.sleep(.3)
        assert job['status'] == 'done', job
        assert job['engine'] == engine
        if args.backend == 'native':
            assert job['hmong_backend'] == 'vits_openvoice_v2' and job['hmong_steps'] is None
        else:
            assert job['hmong_steps'] == 16
        response = client.get('/api/audio/' + job['id'])
        assert response.status_code == 200, response.text
        samples, rate = sf.read(io.BytesIO(response.content), dtype='float32')
        assert rate == 24000 and samples.size > rate / 3
        assert np.all(np.isfinite(samples)) and np.max(np.abs(samples)) > .001
        check_spoken_speed(job)
        assert job['expression']['phrase_context'] is True
        assert job['expression']['emphasis_scope'] == 'phrase'
        return job

    if args.backend == 'f5':
        # A distinct process keeps app/model globals and model caches separate.
        with TestClient(studio.app) as client:
            config = client.get('/api/config').json()
            assert config['hmong_engine'] == 'f5_hmong' and config['hmong_steps'] == 16
            assert config['models']['f5_hmong'] is True
            started = time.monotonic()
            job = render(client, {'text': 'Nyob zoo, kuv yog ib tug Hmoob.', 'language': 'mww',
                                 'voice_id': 'hmong-male', 'format': 'wav', 'paragraph_pause': 0})
            assert job['hmong_precision'] == 'fp32' and job['hmong_device'] == 'cpu'
            compatibility = {'success': True, 'engine': engine, 'steps': 16, 'precision': 'fp32',
                'device': 'cpu', 'real_synthesis': True, 'voice_id': 'hmong-male',
                'audio_seconds': job['audio_seconds'], 'spoken_audio_seconds': job['spoken_audio_seconds'],
                'speed_report': job['speed_report'], 'request_wall_seconds': round(time.monotonic() - started, 3),
                'pronunciation_evaluated': False, 'target_30x_verified': False,
                'cuda_inference_validated': False}
        compatibility['normal_launcher'] = check_web_launcher(root, 'f5')
        reports.mkdir(parents=True, exist_ok=True)
        (reports / 'f5-smoke.json').write_text(json.dumps(compatibility, ensure_ascii=False, indent=2), encoding='utf-8')
        print('PASS: preserved F5 CPU16-step FP32 actual synthesis and normal launcher.', flush=True)
        return

    with TestClient(studio.app) as client:
        config = client.get('/api/config').json()
        assert config['variant'] == 'hmong' and config['default_language'] == 'mww'
        assert config['hmong_engine'] == engine and config['hmong_steps'] is None
        assert config['hmong_backend'] == 'native' and config['default_voice_id'] == 'hmong-male'
        assert config['delivery'] == 'story' and config['emotion'] == 'warm'
        assert config['emotion_strength'] == .65 and config['auto_rhythm'] is False
        assert config['hmong_phrase_context'] is True
        assert config['models'][engine] and not config['nano_ready']
        assert config['subtitle_ready'] is False, 'Do not claim Hmong Whisper recognition'
        for asset in ('app.js', 'workspace.js', 'style.css'):
            assert client.get('/static/' + asset).status_code == 200
        assert 'Voice Studio Hmong' in client.get('/').text
        voices = client.get('/api/voices').json()['voices']
        assert {v['id'] for v in voices} == {'hmong-female', 'hmong-male'}
        for ident, delivery in [('hmong-female', 'review'), ('hmong-male', None)]:
            print('Real offline inference:', ident, delivery, flush=True)
            preset = next(v for v in voices if v['id'] == ident)
            metadata = voice_metadata[ident.removeprefix('hmong-')]
            source = app_root / 'assets/hmong' / metadata['file']
            assert source.suffix == '.mp3', 'Preset preview must retain the complete supplied MP3'
            assert hashlib.sha256(source.read_bytes()).hexdigest() == metadata['sha256']
            preview = client.get(preset['sample_url'])
            assert preview.status_code == 200
            assert hashlib.sha256(preview.content).hexdigest() == metadata['sha256']
            results['full_source_previews'][ident] = {'sha256': metadata['sha256'],
                'source_seconds': metadata['duration'], 'user_filename': metadata['user_filename'],
                'reference_start': metadata['reference']['start'],
                'reference_end': metadata['reference']['end']}
            started = time.monotonic()
            spoken_text = EXPRESSIVE_SAMPLE if ident == 'hmong-male' else text
            payload = {'text': spoken_text, 'language': 'mww', 'voice_id': ident,
                       'format': 'wav', 'speed': 1, 'paragraph_pause': 0}
            if delivery is not None:
                payload['delivery'] = delivery
            if ident == 'hmong-male':
                payload['emotion'] = 'warm'
            job = render(client, payload)
            results['voices'][ident] = {'audio_seconds': job['audio_seconds'],
                                      'spoken_audio_seconds': job['spoken_audio_seconds'],
                                      'inserted_silence_seconds': job['inserted_silence_seconds'],
                                      'speed_report': job['speed_report'],
                                      'wall_seconds': round(time.monotonic() - started, 3),
                                      'engine': job['engine'], 'backend': job['hmong_backend'],
                                      'steps': job['hmong_steps'], 'precision': job['hmong_precision']}
            assert job['hmong_steps'] is None and job['hmong_precision'] == 'fp32'
            assert job['hmong_device'] == 'cpu'
            assert job['segment_plan'] == 'hmong-expression-v1'
            assert job['hmong_phrase_context'] is True and job['auto_rhythm'] is False
            if ident == 'hmong-male':
                assert job['delivery'] == 'story'
                expression = job['expression']
                assert expression['controls_version'] == 'hmong-expression-v1'
                assert expression['mode'] == 'rhythm_dynamics_v1'
                assert expression['emotion'] == 'warm' and expression['strength'] == .65
                assert expression['auto_rhythm'] is False
                assert expression['phrase_context'] is True and expression['emphasis_scope'] == 'phrase'
                assert expression['pitch_shift'] is False and expression['neural_emotion'] is False
                assert expression['emotions_used'] == ['warm', 'serious']
                assert expression['emotion_counts'] == {'warm': 1, 'serious': 1}
                assert job['inserted_silence_seconds'] >= .25 - 1 / 24000
                results['expression'] = {'voice_id': ident, 'steps': job['hmong_steps'],
                    'precision': job['hmong_precision'], 'markup_removed_from_spoken_srt': False,
                    **expression}
            txt = client.get('/api/jobs/' + job['id'] + '/script.txt')
            srt = client.get('/api/jobs/' + job['id'] + '/script.srt')
            assert txt.status_code == srt.status_code == 200
            assert spoken_text in txt.text and '-->' in srt.text and 'Peb ua' in srt.text
            assert all(re.search(r'\b' + word + r'\b', srt.text) for word in PRONUNCIATION_TEST_WORDS)
            if ident == 'hmong-male':
                assert '[emotion=' not in srt.text and '[pause=' not in srt.text and '**' not in srt.text
                results['expression']['markup_removed_from_spoken_srt'] = True
            results['txt_srt'] = True
            results['generated_auditions'][ident] = export_generated_preview(client, job, reports)
            pipeline_wall = time.monotonic() - started
            results['generated_auditions'][ident]['full_pipeline'] = {
                'wall_seconds': round(pipeline_wall, 3),
                'worker_wall_seconds': job['wall_processing_seconds'],
                'spoken_realtime_multiplier': round(job['spoken_audio_seconds'] / pipeline_wall, 3),
                'includes': ['speech_request', 'model_loading_when_needed',
                             'reference_embedding_when_needed', 'VITS', 'OpenVoice_conversion',
                             'watermark_when_audio_long_enough',
                             'expression', 'job_polling', 'WAV_readback', 'TXT_SRT_export',
                             'MP3_export', 'ffprobe'],
                'model_cache': 'process_first_job' if ident == 'hmong-female' else 'warm_process',
                'estimate_only': True, 'target_30x_verified_one_hour': False}
        assert len(results['generated_auditions']) == 2
        results['mp3'] = True

        for gender in ('female', 'male'):
            metadata = voice_metadata[gender]
            source = app_root / 'assets/hmong' / metadata['file']
            with source.open('rb') as audio:
                response = client.post('/api/voices/clone', data={'name': 'Native QA source ' + gender,
                    'language': 'mww', 'transcript': '', 'consent': 'true'},
                    files={'file': (source.name, audio, 'audio/mpeg')})
            assert response.status_code == 201, response.text
            personal = response.json()
            check_source_reference(personal, metadata, gender, engine=engine)
            started = time.monotonic()
            clone = render(client, {'text': 'Kuv zoo siab tau ntsib nej.', 'language': 'mww',
                                   'voice_id': personal['id'],
                                   'format': 'wav', 'paragraph_pause': 0})
            assert clone['engine'] == engine
            assert clone['hmong_steps'] is None and clone['hmong_precision'] == 'fp32'
            results['source_clones'][gender] = {
                'source_sha256': personal['source_sha256'], 'source_seconds': personal['source_duration'],
                'reference_seconds': personal['duration'], 'automatic_reference': True,
                'audio_seconds': clone['audio_seconds'],
                'spoken_audio_seconds': clone['spoken_audio_seconds'],
                'inserted_silence_seconds': clone['inserted_silence_seconds'],
                'speed_report': clone['speed_report'],
                'engine': clone['engine'], 'backend': clone['hmong_backend'],
                'steps': clone['hmong_steps'], 'precision': clone['hmong_precision'],
                'wall_seconds': round(time.monotonic() - started, 3)}
        results['clone'] = True

        # A different long file needs an explicit excerpt and matching words.
        # Prefix supplied speech with one second of silence and shift the
        # manifest's reference bounds by the same amount. Keep the complete
        # supplied MP3 for previews, including any silence outside the excerpt.
        female = voice_metadata['female']
        source = app_root / 'assets/hmong' / female['file']
        manual_start = 1 + female['reference']['start']
        manual_end = 1 + female['reference']['end']
        reference_seconds = female['reference']['end'] - female['reference']['start']
        altered = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(source),
            '-af', 'adelay=1000:all=1,apad', '-t', str(max(12, manual_end + 1)), '-ac', '1', '-ar', '24000',
            '-codec:a', 'pcm_s16le', '-f', 'wav', 'pipe:1'], timeout=45)
        assert sf.info(io.BytesIO(altered)).duration >= 11.99
        assert hashlib.sha256(altered).hexdigest() not in {v['sha256'] for v in voice_metadata.values()}
        fields = {'name': 'Native QA manual crop', 'language': 'mww', 'consent': 'true'}
        files = {'file': ('different-long.wav', altered, 'audio/wav')}
        missing = client.post('/api/voices/clone', data=fields, files=files)
        assert missing.status_code == 422, 'Unknown long audio must not guess words or reference bounds'
        fields.update(transcript=female['reference']['text'], reference_start=str(manual_start),
                      reference_end=str(manual_end))
        response = client.post('/api/voices/clone', data=fields, files=files)
        assert response.status_code == 201, response.text
        manual = response.json()
        assert manual['engine'] == engine and manual['automatic_reference'] is False
        assert manual['transcript'] == female['reference']['text']
        assert abs(manual['reference_start'] - manual_start) < .01
        assert abs(manual['reference_end'] - manual_end) < .01
        assert abs(manual['duration'] - reference_seconds) < .05
        manual_job = render(client, {'text': 'Peb zoo siab tau nyob ua ke.', 'language': 'mww',
                                    'voice_id': manual['id'],
                                    'format': 'wav', 'paragraph_pause': 0})
        assert manual_job['engine'] == engine
        results['manual_crop'] = True
        srt_text = '1\n00:00:00,000 --> 00:00:12,000\nNyob zoo, kuv yog ib tug Hmoob.\n'
        aligned = render(client, {'text': srt_text, 'input_format': 'srt', 'language': 'mww',
                                 'voice_id': 'hmong-female',
                                 'format': 'wav', 'paragraph_pause': 0, 'max_cue_tempo': 2})
        assert abs(aligned['audio_seconds'] - 12) < .1
        assert aligned['spoken_audio_seconds'] < aligned['audio_seconds']
        assert aligned['inserted_silence_seconds'] > 0
        results['srt_speed_report'] = aligned['speed_report']
        saved = client.get('/api/jobs/' + aligned['id'] + '/script.srt')
        assert saved.status_code == 200 and '00:00:12,000' in saved.text
        results['srt_timeline'] = True

    results['default_synthesis'] = {'engine': engine, 'backend': 'vits_openvoice_v2',
                                   'steps': None, 'precision': 'fp32', 'device': 'cpu',
                                   'presets_tested': 2, 'source_clones_tested': 2}
    results['pronunciation_evaluated'] = False
    results['reference_text_verified'] = True
    results['reference_text_source'] = 'user_provided_for_selected_excerpt'
    results['batch_entrypoints'] = check_batch_entrypoints(root)
    results['fast_launcher'] = check_web_launcher(root, 'native')
    results['success'] = True
    reports.mkdir(parents=True, exist_ok=True)
    (reports / 'native-smoke.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PASS: CPU native VITS/OpenVoice presets/clones, six-word generated MP3s, expression, '
          'full-pipeline timings, SRT and12 BAT paths. CUDA inference, pronunciation and30x remain unverified.', flush=True)


def check_web_launcher(root, backend):
    """Start the selected application using the actual relocated launcher."""
    root = Path(root)
    app_root = root / 'voice-studio-hmong'
    environment = dict(os.environ, HMOOB_BACKEND=backend)
    engine = 'hmong_native' if backend == 'native' else 'f5_hmong'
    subprocess.run([sys.executable, str(app_root / 'hmong_launcher.py'), '--check'],
                   check=True, cwd=app_root, env=environment, timeout=180)
    print('Checking Hmong launcher after relocation:', backend, flush=True)
    process = subprocess.Popen([sys.executable, str(app_root / 'hmong_launcher.py'), '--no-browser'],
        cwd=app_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding='utf-8', errors='replace')
    lines = queue.Queue()
    def read_output():
        for line in process.stdout:
            print(line.rstrip(), flush=True)
            lines.put(line)
    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    ready = False
    try:
        deadline = time.monotonic() + 180
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError('Hmong launcher exited: ' + str(process.returncode))
            try:
                line = lines.get(timeout=.25)
            except queue.Empty:
                continue
            match = re.search(r'Studio:\s*(http://127\.0\.0\.1:\d+)', line)
            if not match:
                continue
            with opener.open(match[1] + '/api/config', timeout=5) as response:
                live = json.load(response)
            assert live['variant'] == 'hmong' and live['models'][engine] and live['hmong_engine'] == engine
            assert live['hmong_steps'] == (None if backend == 'native' else 16)
            ready = True
            break
        assert ready, 'Launcher readiness timed out: ' + backend
    finally:
        if process.poll() is None:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                process.terminate()
            process.wait(timeout=30)
        reader.join(timeout=2)
    return ready


if __name__ == '__main__':
    main()
