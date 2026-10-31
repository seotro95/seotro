"""Run offline Windows checks with the Python inside an extracted clean bundle.

This checks the actual relocated runtime, public Nano/Turbo synthesis and ASGI
exports. It neither decrypts private voice references nor tests CUDA inference.
Native VoxCPM2 PCM is checked separately by smoke_native_voxcpm.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def configure(root):
    runtime, data = root / 'runtime', root / 'app/.data'
    if os.name != 'nt' or sys.platform != 'win32':
        raise RuntimeError('This check must run on actual Windows')
    if Path(sys.executable).resolve().parent != runtime or Path(sys.prefix).resolve() != runtime:
        raise RuntimeError('Run with the relocated bundled runtime/python.exe')
    for key in ('PYTHONHOME', 'PYTHONPATH', 'TRANSFORMERS_CACHE'):
        os.environ.pop(key, None)
    os.environ.update(
        PYTHONNOUSERSITE='1', PYTHONUTF8='1',
        VOICE_STUDIO_DATA_DIR=str(data), VOICE_STUDIO_NATIVE_ROOT=str(root / 'runtime-native'),
        HF_HOME=str(data / 'models/cache'), HF_HUB_CACHE=str(data / 'models/cache/hub'),
        HUGGINGFACE_HUB_CACHE=str(data / 'models/cache/hub'),
        HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_XET='1',
        HF_HUB_DISABLE_TELEMETRY='1', GRADIO_ANALYTICS_ENABLED='False', DO_NOT_TRACK='1',
    )
    os.environ['PATH'] = str(root / 'ffmpeg/bin') + os.pathsep + str(runtime) + os.pathsep + os.environ.get('PATH', '')
    sys.path.insert(0, str(root / 'app'))
    return runtime, data


def check_packaging(root):
    required = ('CLEANUP-REPORT.json', 'BUILD_INFO.json', 'MANIFEST.sha256',
                'BUNDLED-PACKAGES.txt', 'MO_TOOL.bat', 'CAI_19_GIONG.bat',
                'install_secure_voices.ps1', 'delivery/manifest.json', 'delivery/voices.vspack',
                'app/.data/models/vieneu_nano.ready', 'app/.data/models/vieneu.ready',
                'app/.data/models/voxcpm-native.ready',
                'runtime-native/cpu/audiocpp.dll', 'runtime-native/cuda/audiocpp.dll')
    for name in required:
        if not (root / name).is_file():
            raise ValueError('Missing required clean-bundle file: ' + name)
    build = json.loads((root / 'BUILD_INFO.json').read_text(encoding='utf-8'))
    if build.get('version') != '1.12.1' or build.get('package_revision') != 'clean-2':
        raise ValueError('Expected application 1.12.1 with clean-2 package revision')
    launcher = (root / 'MO_TOOL.bat').read_text(encoding='utf-8-sig')
    if '1.12.1' not in launcher or '1.9.0' in launcher:
        raise ValueError('The launcher still identifies an obsolete version')
    manifest = json.loads((root / 'delivery/manifest.json').read_text(encoding='utf-8-sig'))
    if manifest.get('format') != 'voice-studio-private-delivery-v1' or manifest.get('encrypted_file') != 'voices.vspack':
        raise ValueError('The original encrypted voice delivery manifest is missing')
    encrypted = root / 'delivery/voices.vspack'
    if encrypted.stat().st_size != manifest.get('encrypted_size') or digest(encrypted) != manifest.get('encrypted_sha256'):
        raise ValueError('The encrypted voice pack does not match its original manifest')
    return {'clean_package_revision': 'clean-2', 'encrypted_voice_pack_sha256': digest(encrypted),
            'encrypted_voice_pack_preserved': True, 'private_voice_unlock_attempted': False,
            'private_voice_identity_or_count_independently_verified': False,
            'launcher_identifies_current_version': True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.output.exists():
        raise FileExistsError('Choose a new smoke-report path')
    runtime, data = configure(root)
    package_checks = check_packaging(root)
    import numpy as np
    import onnxruntime
    import soundfile as sf
    import httpx
    import psutil
    from fastapi.testclient import TestClient
    import app as studio
    from subtitles import parse_srt
    from worker import render, close_nano_pool, close_international_backends

    if Path(studio.__file__).resolve() != root / 'app/app.py' or studio.DATA != data:
        raise ValueError('The check imported a different application or data directory')
    modules = (np, onnxruntime, sf, httpx, psutil)
    for module in modules:
        if runtime not in Path(module.__file__).resolve().parents:
            raise ValueError('Dependency escaped bundled Python: ' + module.__name__)
    for binary in ('ffmpeg', 'ffprobe'):
        located = shutil.which(binary)
        if not located or Path(located).resolve().parent != root / 'ffmpeg/bin':
            raise ValueError('Audio binary escaped bundled FFmpeg: ' + binary)
        subprocess.run([located, '-version'], check=True, stdout=subprocess.DEVNULL, timeout=30)
    subprocess.run([sys.executable, '-s', '-m', 'pip', 'check'], check=True, timeout=120)

    def pcm(path):
        audio, rate = sf.read(path, dtype='float32')
        if rate != 24000 or audio.ndim != 1 or len(audio) < rate * .3:
            raise ValueError('Synthesis did not create the expected mono 24 kHz PCM')
        if not np.isfinite(audio).all() or np.max(np.abs(audio)) <= .001:
            raise ValueError('Synthesis produced invalid or silent PCM')
        return audio, rate

    rendered = []
    public_text = 'Xin chào. Đây là bản kiểm tra giọng nói tiếng Việt.'
    base = {'language': 'vi', 'quality': 'standard', 'speed': 1, 'nano_steps': 8,
            'nano_threads': 2, 'nano_parallel': 1, 'paragraph_pause': 0,
            'model_memory': 'shared', 'resource_profile': 'maximum',
            'input_format': 'txt', 'text': public_text, 'format': 'wav',
            'render_mode': 'balanced', 'audio_fit_backend': 'wsola', 'delivery': 'natural'}
    srt_text = ('1\n00:00:00,250 --> 00:00:02,000\nXin chào.\n\n'
                '2\n00:00:02,500 --> 00:00:04,750\nCảm ơn.\n')
    try:
        with TestClient(studio.app) as client:
            config_response = client.get('/api/config')
            if config_response.status_code != 200:
                raise ValueError('Application configuration request failed')
            config = config_response.json()
            if (config.get('version') != '1.12.1' or config.get('edition') != 'standalone-voice'
                    or not config.get('nano_ready') or not config.get('models', {}).get('vieneu')
                    or not config.get('native_voxcpm_ready') or not config.get('native_voxcpm_cpu_available')):
                raise ValueError('The clean application does not report its bundled engines ready')
            for url, expected in (('/', None), ('/static/app.js', root / 'app/static/app.js'),
                                  ('/static/style.css', root / 'app/static/style.css')):
                response = client.get(url)
                if response.status_code != 200 or (expected is not None and response.content != expected.read_bytes()):
                    raise ValueError('UI asset did not match the clean package: ' + url)
            catalog = client.get('/api/voices')
            if catalog.status_code != 200:
                raise ValueError('Voice catalog request failed')
            voices = catalog.json()['voices']
            if not all(any(v.get('engine') == engine and v.get('ready') for v in voices)
                       for engine in ('vieneu_nano', 'vieneu')):
                raise ValueError('Public Nano/Turbo presets are not ready')
            hardware = client.get('/api/system-info?quick=true')
            if hardware.status_code != 200 or hardware.json().get('physical_cores', 0) < 1 or not hardware.json().get('ram_gb'):
                raise ValueError('Hardware detection did not work with the cleaned runtime')
            conversion = client.post('/api/scripts/convert', json={
                'text': public_text, 'input_format': 'txt', 'output_format': 'txt'})
            if conversion.status_code != 200 or conversion.json().get('text') != public_text:
                raise ValueError('The TXT converter did not preserve public input text')

            jobs = [dict(base, id=uuid.uuid4().hex, engine='vieneu_nano',
                         voice_id='nano-minhquan', speaker='Minh Quân'),
                    dict(base, id=uuid.uuid4().hex, engine='vieneu',
                         voice_id='vi-maianh', speaker='Mai Anh', format='mp3'),
                    dict(base, id=uuid.uuid4().hex, engine='vieneu_nano',
                         voice_id='nano-minhquan', speaker='Minh Quân', text=srt_text,
                         input_format='srt', cue_fit='auto', max_cue_tempo=1.5)]
            for job in jobs:
                started = time.perf_counter()
                render(job)
                elapsed = time.perf_counter() - started
                output = data / 'audio' / (job['id'] + '.' + job['format'])
                check_audio = output
                if job['format'] == 'mp3':
                    check_audio = data / 'parts' / job['id'] / 'decoded-mp3.wav'
                    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(output),
                                    '-ac', '1', '-ar', '24000', '-codec:a', 'pcm_s16le', str(check_audio)],
                                   check=True, timeout=60)
                samples, rate = pcm(check_audio)
                sidecar = data / 'audio' / (job['id'] + '.srt')
                parsed = parse_srt(sidecar.read_text(encoding='utf-8'))
                if job['input_format'] == 'srt':
                    if parsed != parse_srt(srt_text) or len(samples) != round(4.75 * rate):
                        raise ValueError('Actual Nano SRT output did not preserve both subtitle clocks')
                    if np.any(samples[:round(.25 * rate)]):
                        raise ValueError('Subtitle audio started before the first cue')
                    alignment = json.loads((data / 'parts' / job['id'] / 'alignment.json').read_text(encoding='utf-8'))
                    if not alignment.get('sync_ok') or len(alignment.get('cues', [])) != 2:
                        raise ValueError('Actual Nano subtitle alignment was incomplete')
                studio.write_json(data / 'jobs' / (job['id'] + '.json'), {**job, 'status': 'done'})
                expected_txt = '\n'.join(cue['text'] for cue in parsed) if job['input_format'] == 'srt' else job['text']
                txt_export = client.get('/api/jobs/' + job['id'] + '/script.txt')
                srt_export = client.get('/api/jobs/' + job['id'] + '/script.srt')
                audio_export = client.get('/api/audio/' + job['id'])
                if txt_export.status_code != 200 or txt_export.text != expected_txt:
                    raise ValueError('The synthesized job TXT export was incorrect')
                if srt_export.status_code != 200 or parse_srt(srt_export.text) != parsed:
                    raise ValueError('The synthesized job SRT export was incorrect')
                if audio_export.status_code != 200 or hashlib.sha256(audio_export.content).hexdigest() != digest(output):
                    raise ValueError('The synthesized job audio export did not match its file')
                rendered.append({'engine': job['engine'], 'public_preset': job['speaker'],
                                 'input_format': job['input_format'], 'output_format': job['format'],
                                 'valid_pcm': True, 'audio_seconds': len(samples) / rate,
                                 'processing_seconds': round(elapsed, 3),
                                 'txt_srt_and_audio_exports_passed': True,
                                 'two_subtitle_clocks_preserved': job['input_format'] == 'srt'})
        report = {'format': 'voice-studio-clean-windows-smoke-v1', 'platform': sys.platform,
                  'product_version': '1.12.1', 'source_commit': os.environ.get('GITHUB_SHA'),
                  'bundled_python_relocated': True, 'bundled_dependencies_imported': True,
                  'pip_check_passed': True, 'bundled_ffmpeg_and_ffprobe_passed': True,
                  'app_http_smoke_passed': True, 'ui_assets_match_extracted_package': True,
                  'native_voxcpm_reported_ready': True, 'native_inference_tested_here': False,
                  'public_nano_turbo_real_synthesis_passed': True, 'requests': rendered,
                  **package_checks, 'gpu_inference_tested': False, 'gtx1060_tested': False,
                  'full_hour_generated': False, 'target_30x_guaranteed': False,
                  'human_pronunciation_reviewed': False}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8', newline='\n') as destination:
            json.dump(report, destination, ensure_ascii=False, indent=2)
            destination.write('\n')
        print(json.dumps(report, ensure_ascii=False), flush=True)
    finally:
        close_nano_pool()
        close_international_backends()


if __name__ == '__main__':
    main()
