"""Prove native first-run preparation and speech from an empty Windows bundle.

This is deliberately run before F5 preparation or any prepared-data reuse.
Only the builder-owned portable output is accepted; no existing data is removed.
"""
from __future__ import annotations

import argparse
from array import array
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import wave


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def wave_evidence(path):
    """Read the generated file independently of the launcher's claimed metrics."""
    path = Path(path)
    return wave_evidence_bytes(path.read_bytes(), path.name)


def wave_evidence_bytes(raw, name):
    """Use the same actual PCM check when reopening the final public ZIP."""
    with wave.open(io.BytesIO(raw), 'rb') as audio:
        channels, width, rate, frames = (audio.getnchannels(), audio.getsampwidth(),
                                         audio.getframerate(), audio.getnframes())
        if channels != 1 or width != 2 or rate != 24000 or frames < 8000:
            raise RuntimeError('First-run voice test did not produce usable mono 24 kHz PCM16 speech')
        samples = array('h', audio.readframes(frames))
    if sys.byteorder != 'little':
        samples.byteswap()
    if len(samples) != frames:
        raise RuntimeError('First-run diagnostic WAV is truncated')
    peak = max(abs(value) for value in samples) / 32768
    rms = math.sqrt(sum(value * value for value in samples) / len(samples)) / 32768
    if peak <= .001 or rms <= .00001:
        raise RuntimeError('First-run voice test produced silent audio')
    return {'output': name, 'output_sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
            'sample_rate': rate, 'channels': channels, 'sample_width': width, 'frames': frames,
            'duration_seconds': frames / rate, 'peak': peak, 'rms': rms}


def run_first_start(root, reports):
    if os.name != 'nt' or sys.maxsize <= 2 ** 32:
        raise RuntimeError('Fresh first-run QA requires native Windows x64')
    root, reports = Path(root).resolve(), Path(reports).resolve()
    app, data = root / 'voice-studio-hmong', root / 'voice-studio-hmong/.data'
    if data.exists():
        raise ValueError('First-run QA requires nonexistent data; existing user or builder files are preserved')
    if Path(sys.executable).resolve() != (root / 'runtime/python.exe').resolve():
        raise RuntimeError('First-run QA must execute the actual packaged Python runtime')
    # Explicit local cache paths prevent a builder/user cache from making an
    # unprepared download look ready. The public base contributes runtime only.
    environment = dict(os.environ, VOICE_STUDIO_VARIANT='hmong', HMOOB_BACKEND='native',
        HMOOB_DEVICE='cpu', VOICE_STUDIO_DATA_DIR=str(data), HMOOB_MODEL_DIR=str(data / 'models'),
        HF_HOME=str(data / 'models/cache'), HF_HUB_CACHE=str(data / 'models/cache/hub'),
        HUGGINGFACE_HUB_CACHE=str(data / 'models/cache/hub'),
        TRANSFORMERS_CACHE=str(data / 'models/cache/transformers'),
        TORCH_HOME=str(data / 'models/cache/torch'), PYTHONNOUSERSITE='1', PYTHONUTF8='1',
        HF_HUB_DISABLE_XET='1', PYTHONUNBUFFERED='1',
        PATH=str(root / 'runtime') + os.pathsep + str(root / 'ffmpeg/bin')
             + os.pathsep + os.environ.get('PATH', ''))
    for name in ('PYTHONHOME', 'PYTHONPATH'):
        environment.pop(name, None)
    steps = []

    def launch(flag, *, offline, expected=0, timeout=300, overrides=None):
        env = dict(environment)
        env.update(overrides or {})
        for name in ('HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE'):
            if offline:
                env[name] = '1'
            else:
                env.pop(name, None)
        started = time.monotonic()
        completed = subprocess.run([env.get('COMSPEC', 'cmd.exe'), '/d', '/c',
            'MO_VOICE_STUDIO_HMONG.bat', flag], cwd=root, env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace', timeout=timeout)
        print(completed.stdout, end='', flush=True)
        steps.append({'argument': flag, 'offline': offline, 'exit_code': completed.returncode,
                      'environment_overrides': dict(overrides or {}),
                      'elapsed_seconds': time.monotonic() - started, 'output': completed.stdout})
        if completed.returncode != expected:
            raise RuntimeError('Fresh first-run launcher failed: ' + flag +
                               ', exit ' + str(completed.returncode))
        return completed

    reports.mkdir(parents=True, exist_ok=True)
    report = {'schema_version': 1, 'version': '1.6.2', 'success': False, 'platform': sys.platform,
              'native_windows_validation': True, 'actual_cmd_batch': True,
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
              'initial_data_absent': True,
              'prepared_models_reused': False, 'external_model_cache_used': False,
              'runtime_python_sha256': digest(root / 'runtime/python.exe'), 'steps': steps}
    try:
        launch('--check', offline=True, expected=1)
        model_files = [path for path in (data / 'models').rglob('*') if path.is_file()]
        if model_files:
            raise RuntimeError('Missing-model offline check unexpectedly created model files')
        report['missing_models_rejected_offline'] = True
        launch('--probe-runtime', offline=True)
        runtime = json.loads((data / 'diagnostics/runtime-check.json').read_text(encoding='utf-8'))
        if runtime.get('ok') is not True or runtime.get('inference_tested') is not False:
            raise RuntimeError('Fresh runtime probe did not pass its actual library/tensor checks')
        report['runtime_health'] = runtime
        launch('--setup-only', offline=False, timeout=2400)
        manifest = data / 'models/verified-native-models.json'
        if not manifest.is_file():
            raise RuntimeError('First-run preparation did not write the verified native model manifest')
        report['model_manifest_sha256'] = digest(manifest)
        report['models_prepared_from_empty_data'] = True
        launch('--check', offline=True)
        completed = launch('--test-voice', offline=True, timeout=600,
                           overrides={'HMOOB_DEVICE': 'cuda', 'HMOOB_PRECISION': 'int8'})
        speech = json.loads((data / 'diagnostics/speech-check.json').read_text(encoding='utf-8'))
        if (speech.get('ok') is not True or speech.get('inference_tested') is not True
                or [item.get('id') for item in speech.get('voices', [])] != ['hmong-male', 'hmong-female']):
            raise RuntimeError('First-run speech diagnostic did not actually complete both default voices')
        report['speech_check'] = speech
        report['legacy_environment_recovery'] = {
            'requested_device': 'cuda', 'requested_precision': 'int8',
            'effective_device': speech.get('device'),
            'effective_precision': speech.get('configuration', {}).get('precision'),
            'fallback_notice': 'Đang dùng bộ CPU để tạo giọng' in completed.stdout,
            'int8_notice': 'Đã bỏ tùy chọn INT8 của F5 cũ' in completed.stdout,
            'real_synthesis': speech.get('ok') is True and speech.get('inference_tested') is True}
        voices = []
        for gender, claimed in zip(('male', 'female'), speech['voices']):
            audio = data / ('diagnostics/test-' + gender + '.wav')
            measured = wave_evidence(audio)
            if measured['output_sha256'] != claimed.get('output_sha256'):
                raise RuntimeError('First-run speech report hash differs from actual WAV')
            voices.append(dict(measured, id='hmong-' + gender,
                               reference_fingerprint=claimed.get('reference_fingerprint')))
            shutil.copy2(audio, reports / ('first-run-' + gender + '.wav'))
        report['independently_verified_voices'] = voices
        report['success'] = True
        return report
    finally:
        (reports / 'fresh-start.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('reports', type=Path)
    args = parser.parse_args()
    run_first_start(args.root, args.reports)


if __name__ == '__main__':
    main()
