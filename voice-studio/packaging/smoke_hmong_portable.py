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
import tempfile
import threading
import time
import urllib.request
import uuid
import zipfile
from unittest.mock import patch


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
    entries = [('MO_VOICE_STUDIO_HMONG.bat', '--check', 'native'),
               ('tools/launch_hmong.bat', '--setup-only', 'native'),
               ('tools/MO_F5_HMONG.bat', '--check', 'f5'),
               ('tools/KIEM_TRA_HMONG.bat', '--check', 'native'),
               ('tools/install_hmong_cuda.bat', '--check', 'native')]
    results = {}
    shell = os.environ.get('COMSPEC', 'cmd.exe')
    for relative, flag, backend in entries:
        batch = root / relative
        print('Native cmd.exe entrypoint:', relative, flag, flush=True)
        # The working directory itself contains spaces after relocation. The
        # ASCII basename avoids cmd's special handling of a quoted /c command.
        # Root/F5 wrappers must override a conflicting inherited backend.
        inherited_backend = ('f5' if backend == 'native' else 'native') if relative in {
            'MO_VOICE_STUDIO_HMONG.bat', 'tools/MO_F5_HMONG.bat'} else 'native'
        environment = dict(os.environ, HMOOB_BACKEND=inherited_backend)
        completed = subprocess.run([shell, '/d', '/c', batch.name, flag], cwd=batch.parent, env=environment,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace', timeout=180)
        print(completed.stdout, end='', flush=True)
        label = 'Hmong nhanh thử nghiệm' if backend == 'native' else 'F5-Hmong'
        if completed.returncode or 'PASS:' not in completed.stdout or label not in completed.stdout:
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


def check_longform(client, studio, template):
    """Check full-size acceptance/planning, then real bounded chapter speech.

    The million-character request never starts inference. Only chapter planning
    is injected for the short, two-part real synthesis; the controller, worker,
    reference validation, audio files, archive and download routes stay real.
    """
    import longform
    from narration import plan_segments
    text = ('Nyob zoo. ' * 100001)[:1_000_000]
    with patch.object(studio.executor, 'submit') as queued:
        response = client.post('/api/speech', json={'text': text, 'language': 'mww',
            'voice_id': 'hmong-male', 'format': 'wav', 'paragraph_pause': 0})
        assert response.status_code == 202, response.text
        full = response.json()
        assert len(full['text']) == 1_000_000 and full['longform'] is True
        queued.assert_called_once()
    chapters = longform.plan_chapters(full)
    assert len(chapters) > 1 and all(chapter.characters <= longform.PART_CHARACTERS for chapter in chapters)
    assert [segment for chapter in chapters for segment in chapter.segments] == plan_segments(full)
    assert client.post('/api/speech', json={'text': text + 'a', 'language': 'mww',
        'voice_id': 'hmong-male'}).status_code == 422
    full.update(status='cancelled', error='Builder QA: acceptance/planning only; inference was never submitted.')
    studio.write_json(studio.DATA / 'jobs' / (full['id'] + '.json'), full)

    source = '[emotion=warm]Nyob zoo.[emotion=serious]Ua tsaug.'
    job = {**template, 'id': uuid.uuid4().hex, 'text': source, 'input_format': 'txt',
           'format': 'wav', 'longform': True, 'status': 'running', 'paragraph_pause': 0,
           'created_at': studio.now(), 'qa_release_longform': True}
    for key in ('character_cast', 'character_voices', 'cue_characters', 'video_id'):
        job.pop(key, None)
    segments = plan_segments(job)
    assert len(segments) == 2 and all(segment.text for segment in segments)
    short_chapters = [longform.Chapter(index + 1, index, index + 1, (segment,), len(segment.text))
                      for index, segment in enumerate(segments)]
    with patch.object(longform, 'plan_chapters', return_value=short_chapters):
        result = longform.run_longform(job, studio.DATA, studio.execute_worker, dict(os.environ))
    assert result['chapter_count'] == result['completed_chapters'] == 2
    assert result['completed'] == result['total'] == 2 and result['duration_limited'] is False
    job.update(result, status='done', url='/api/jobs/' + job['id'] + '/archive', finished_at=studio.now())
    studio.write_json(studio.DATA / 'jobs' / (job['id'] + '.json'), job)
    response = client.get(job['url'])
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.testzip() is None and archive.read('original.txt').decode('utf-8') == source
        manifest = json.loads(archive.read('manifest.json'))
        assert manifest['chapter_count'] == 2 and manifest['source_characters'] == len(source)
        for chapter in manifest['chapters']:
            from browser_hmong_portable import audio_evidence
            audio = archive.read(chapter['files']['audio'])
            audio_evidence(audio)
            assert archive.read(chapter['files']['txt']).strip()
            assert b'-->' in archive.read(chapter['files']['srt'])
            preview = client.get(f"/api/jobs/{job['id']}/chapters/{chapter['index']}")
            assert preview.status_code == 200 and preview.content == audio
    return {'success': True, 'accepted_characters': len(text), 'planned_chapters': len(chapters),
            'million_character_synthesis_performed': False, 'oversize_rejected': True,
            'plan_preserved_all_segments': True, 'real_synthesis': True,
            'short_sample_plan_injected': True, 'sample_characters': len(source),
            'completed_chapters': 2, 'job_id': job['id'], 'archive_bytes': len(response.content),
            'archive_sha256': hashlib.sha256(response.content).hexdigest(),
            'archive_contents_verified': True, 'chapter_routes_verified': True}


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
    from hmong_native import REFERENCE_CACHE_SIZE
    assert REFERENCE_CACHE_SIZE == 16
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
               'txt_srt': False, 'mp3': False, 'main_launcher': False, 'batch_entrypoints': {},
               'expression': {}, 'generated_auditions': {},
               'reference_cache_limit': REFERENCE_CACHE_SIZE,
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
        compatibility['advanced_f5_launcher'] = check_web_launcher(root, 'f5')
        reports.mkdir(parents=True, exist_ok=True)
        (reports / 'f5-smoke.json').write_text(json.dumps(compatibility, ensure_ascii=False, indent=2), encoding='utf-8')
        print('PASS: preserved F5 CPU16-step FP32 actual synthesis and advanced launcher.', flush=True)
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
        quality = manual['quality']
        assert isinstance(quality['advisories'], list) and isinstance(quality['guidance'], list)
        assert isinstance(quality['attention_recommended'], bool)
        assert 'similarity_score' not in quality and 'clone_accuracy' not in quality
        results['reference_quality_advisories'] = True
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
        cast_text = ('1\n00:00:00,000 --> 00:00:12,000\nNyob zoo.\n\n'
                     '2\n00:00:12,000 --> 00:00:24,000\nUa tsaug.\n')
        cast = render(client, {'text': cast_text, 'input_format': 'srt', 'language': 'mww',
            'voice_id': 'hmong-male', 'character_voices': {'narrator': 'hmong-male', 'guest': 'hmong-female'},
            'cue_characters': ['narrator', 'guest'], 'format': 'wav',
            'paragraph_pause': 0, 'max_cue_tempo': 2})
        assert cast['text'] == cast_text and abs(cast['audio_seconds'] - 24) < .1
        snapshots = cast['character_cast']['voices']
        from hmong_assets import reference_fingerprint
        for character, ident in [('narrator', 'hmong-male'), ('guest', 'hmong-female')]:
            assert snapshots[character]['voice_id'] == snapshots[character]['speaker'] == ident
            assert snapshots[character]['hmong_reference_fingerprint'] == reference_fingerprint(ident)
        results['character_cast'] = {'success': True, 'real_synthesis': True, 'job_id': cast['id'],
            'cue_characters': cast['character_cast']['cues'], 'voice_ids': ['hmong-male', 'hmong-female'],
            'reference_identities_verified': True, 'original_srt_preserved': True,
            'audio_seconds': cast['audio_seconds']}
        results['longform'] = check_longform(client, studio, aligned)

        # The browser operates this real local video and imports its SRT via
        # the visible project controls; no video/voice API responses are mocked.
        with tempfile.TemporaryDirectory(prefix='hmong-release-video-') as folder:
            video = Path(folder) / 'release-cast-qa.mp4'
            subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
                'color=c=black:s=320x180:r=10', '-t', '24', '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p', str(video)], check=True, timeout=45)
            response = client.post('/api/videos', files={'file': (video.name, video.read_bytes(), 'video/mp4')})
            assert response.status_code == 201, response.text
            results['browser_cast_video_id'] = response.json()['id']

    results['default_synthesis'] = {'engine': engine, 'backend': 'vits_openvoice_v2',
                                   'steps': None, 'precision': 'fp32', 'device': 'cpu',
                                   'presets_tested': 2, 'source_clones_tested': 2}
    results['pronunciation_evaluated'] = False
    results['reference_text_verified'] = True
    results['reference_text_source'] = 'user_provided_for_selected_excerpt'
    results['batch_entrypoints'] = check_batch_entrypoints(root)
    results['main_launcher'] = check_web_launcher(root, 'native', reports=reports)
    results['success'] = True
    reports.mkdir(parents=True, exist_ok=True)
    (reports / 'native-smoke.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PASS: CPU native VITS/OpenVoice presets/clones, six-word generated MP3s, expression, '
          'full-pipeline timings, SRT and5 BAT paths. CUDA inference, pronunciation and30x remain unverified.', flush=True)


def check_browser_selection(root, url, reports):
    """Keep browser tooling outside the package while exercising its real server."""
    interpreter = os.environ.get('HMOOB_BROWSER_PYTHON')
    if not interpreter:
        raise RuntimeError('A separate HMOOB_BROWSER_PYTHON is required for real Windows browser QA')
    interpreter = Path(interpreter).resolve()
    if not interpreter.is_file() or Path(root).resolve() in interpreter.parents:
        raise RuntimeError('The browser QA interpreter must exist outside the portable package')
    from hmong_assets import reference_fingerprint
    expected = {ident: reference_fingerprint(ident) for ident in ('hmong-male', 'hmong-female')}
    # The F5 package's English example is independent of both Hmong defaults.
    # Keep this fixture only in builder-owned QA data, never personal profiles.
    source = Path(root) / 'runtime/Lib/site-packages/f5_tts/infer/examples/basic/basic_ref_en.wav'
    external = Path(reports) / 'external-english-reference.wav'
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(source), '-t', '5',
                    '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le', '-y', str(external)],
                   check=True, capture_output=True, timeout=30)
    script = Path(__file__).with_name('browser_hmong_portable.py')
    subprocess.run([str(interpreter), str(script), '--url', url, '--reports', str(reports),
                    '--expected-references', json.dumps(expected),
                    '--external-reference', str(external)], check=True, timeout=1800)
    report = json.loads((Path(reports) / 'browser-smoke.json').read_text(encoding='utf-8'))
    assert report.get('success') is True and report.get('native_windows_validation') is True
    assert report['runtime']['url'] == url and report['runtime']['backend'] == 'hmong_native'
    assert report['expected_reference_fingerprints'] == expected
    return report


def check_web_launcher(root, backend, *, reports=None):
    """Start once with stale files, then reuse that live server without damage."""
    import psutil

    root = Path(root)
    app_root = root / 'voice-studio-hmong'
    environment = dict(os.environ, HMOOB_BACKEND=backend)
    engine = 'hmong_native' if backend == 'native' else 'f5_hmong'
    relative = 'MO_VOICE_STUDIO_HMONG.bat' if backend == 'native' else 'tools/MO_F5_HMONG.bat'
    entrypoint = root / relative
    shell = os.environ.get('COMSPEC', 'cmd.exe')
    # Exercise exactly the primary BAT users open, including backend selection.
    command = [shell, '/d', '/c', entrypoint.name]
    subprocess.run([*command, '--check'], check=True, cwd=entrypoint.parent, env=environment, timeout=180)
    # This is the builder's isolated QA directory, never an installed user's
    # data. An empty legacy lock reproduced the original Windows startup bug.
    data = Path(environment['VOICE_STUDIO_DATA_DIR'])
    data.mkdir(parents=True, exist_ok=True)
    (data / 'server.lock').write_bytes(b'')
    (data / 'server-instance.json').write_text(json.dumps({
        'instance_id': 'stale-build-qa-instance', 'pid': 2147483647,
        'url': 'http://127.0.0.1:1', 'data_id': 'stale-data',
        'root_id': 'stale-root', 'backend': engine, 'version': '1.5.0-hmong',
    }), encoding='utf-8')
    print('Checking Hmong launcher after relocation:', backend, flush=True)
    process = subprocess.Popen([*command, '--no-browser'],
        cwd=entrypoint.parent, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding='utf-8', errors='replace')
    lines = queue.Queue()
    def read_output():
        for line in process.stdout:
            print(line.rstrip(), flush=True)
            lines.put(line)
    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    ready = False
    result = {}
    try:
        deadline = time.monotonic() + 180
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        def get_json(path):
            with opener.open(url + path, timeout=10) as response:
                return json.load(response)

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
            url = match[1]
            live = get_json('/api/config')
            assert live['variant'] == 'hmong' and live['models'][engine] and live['hmong_engine'] == engine
            assert live['hmong_steps'] == (None if backend == 'native' else 16)
            ready = True
            break
        assert ready, 'Launcher readiness timed out: ' + backend
        instance = get_json('/api/runtime')
        for field in ('instance_id', 'url', 'data_id', 'root_id', 'backend', 'version'):
            assert isinstance(instance.get(field), str) and instance[field], 'Missing runtime identity: ' + field
        assert isinstance(instance.get('pid'), int) and instance['pid'] > 0
        assert instance['url'] == url and instance['backend'] == engine
        assert instance['version'] == live['version'] == '1.6.3-hmong'
        assert instance['instance_id'] != 'stale-build-qa-instance'
        server = psutil.Process(instance['pid'])
        assert server.is_running() and process.pid in {parent.pid for parent in server.parents()}, \
            'The first QA launcher must own the server; never clean up a reused external server'
        history = {job['id']: job['status'] for job in get_json('/api/history')['items']}

        # Keep a real native synthesis active across the second click. F5's
        # separate real-inference check above remains at 16 steps FP32.
        active_job = None
        if backend == 'native':
            payload = {'text': 'Nyob zoo, kuv yog ib tug Hmoob.', 'language': 'mww',
                       'voice_id': 'hmong-male', 'format': 'wav', 'paragraph_pause': 0}
            request = urllib.request.Request(url + '/api/speech',
                data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with opener.open(request, timeout=15) as response:
                assert response.status == 202
                active_job = json.load(response)
            assert active_job['status'] in {'queued', 'running'}
            assert get_json('/api/jobs/' + active_job['id'])['status'] in {'queued', 'running'}, \
                'The native QA job must still be active before the second launch'

        started = time.monotonic()
        # A file avoids waiting for inherited PIPE handles if a broken second
        # launcher starts a child server and then exceeds the timeout.
        with tempfile.TemporaryFile(mode='w+', encoding='utf-8', errors='replace') as output:
            second = subprocess.run([*command, '--no-browser'],
                cwd=entrypoint.parent, env=environment, stdin=subprocess.DEVNULL, stdout=output,
                stderr=subprocess.STDOUT, timeout=15)
            output.seek(0)
            second_output = output.read()
        elapsed = time.monotonic() - started
        print(second_output, end='', flush=True)
        assert second.returncode == 0 and 'REUSED: existing Voice Studio' in second_output, \
            'A second launcher must exit successfully after reusing the live server'
        assert re.findall(r'Studio:\s*(http://127\.0\.0\.1:\d+)', second_output) == [url]
        assert process.poll() is None and server.is_running(), 'The reused server was stopped'
        assert get_json('/api/runtime') == instance, 'The second launch changed the server identity'
        after = {job['id']: job['status'] for job in get_json('/api/history')['items']}
        assert all(after.get(ident) == status for ident, status in history.items()), \
            'The second launcher interrupted or changed existing QA jobs'
        if active_job is not None:
            deadline = time.monotonic() + 600
            while time.monotonic() < deadline:
                job = get_json('/api/jobs/' + active_job['id'])
                assert job['status'] in {'queued', 'running', 'done'}, job
                if job['status'] == 'done':
                    break
                time.sleep(.3)
            assert job['status'] == 'done' and job['engine'] == engine, job
            assert job['audio_seconds'] > 1 / 3
            assert get_json('/api/runtime') == instance
        result = {'ready': True, 'batch_entrypoint': relative, 'actual_cmd_batch': True,
                  'empty_legacy_lock_recovered': True,
                  'stale_instance_metadata_recovered': True, 'second_launch_reused': True,
                  'second_launch_exit_code': second.returncode, 'second_launch_seconds': round(elapsed, 3),
                  'same_url_and_pid': True, 'runtime': instance,
                  'existing_jobs_unchanged': True, 'active_job_preserved': active_job is not None,
                  'active_job_id': active_job['id'] if active_job else None}
        if backend == 'native' and reports is not None:
            result['browser_ui'] = check_browser_selection(root, url, reports)
            assert get_json('/api/runtime') == instance, 'Browser QA changed the running server identity'
    finally:
        # Only the first QA launcher owns a server tree. The second process
        # exits on its own, so it must never be passed to taskkill.
        if process.poll() is None:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                process.terminate()
            process.wait(timeout=30)
        reader.join(timeout=2)
    return result


if __name__ == '__main__':
    main()
