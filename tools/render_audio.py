"""Use the handoff's real Melo/Hmong backends; align every narration to 1292 s."""
import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  MELO_VIET_ROOT='/workspace/restored-mustang/work/melo-runtime',
                  HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import wave
import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, '/workspace/restored-mustang/work/melo-source')
PROFILES = {r['language']: r for r in json.loads((ROOT / 'VOICE_PROFILES.json').read_text())['profiles']}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1024 * 1024): h.update(block)
    return h.hexdigest()


def save(path, data):
    temporary = path.with_suffix('.json.partial')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True)


def render(code, allow_online=False):
    profile = PROFILES[code]
    rows = json.loads((ROOT / 'scripts' / (code + '.json')).read_text())
    assert len(rows) == 129
    report_file = ROOT / 'audio' / (code + '-report.json')
    config_hash = hashlib.sha256(json.dumps({'voice': profile['voice_id'], 'engine': profile['engine'], 'rows': rows}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if report_file.exists():
        previous = json.loads(report_file.read_text())
        if previous.get('config_hash') == config_hash and previous.get('status') == 'created_pending_listening_review':
            if all((ROOT / 'audio' / previous[k]).is_file() and sha(ROOT / 'audio' / previous[k]) == previous[k + '_sha256'] for k in ('mp3', 'flac')):
                print(json.dumps({'code': code, 'status': 'reused_verified_audio'}), flush=True)
                return
    report = {'locale': code, 'voice_id': profile['voice_id'], 'engine': profile['engine'],
              'target_seconds': 1292, 'spoken_cues': 129, 'closing_silence_seconds': 2,
              'config_hash': config_hash, 'status': 'running', 'segments': [],
              'listening_review': 'not a full native-speaker review'}
    save(report_file, report)
    try:
        voice = profile['voice_id']
        if profile.get('runtime_backend') == 'online':
            if not allow_online:
                raise RuntimeError('Enable --allow-online for the verified selected Edge voices.')
            from cloud_edge_trust import configure
            configure()
            from online_backend import handle
            os.environ.pop('HF_HUB_OFFLINE', None)
            os.environ.pop('TRANSFORMERS_OFFLINE', None)
            language = profile['online_locale']
            def speak(text, path):
                for attempt in range(4):
                    try:
                        return handle({'op': 'render', 'language': language, 'voice': voice, 'text': text, 'output': str(path)})
                    except RuntimeError as error:
                        if 'NoAudioReceived' not in str(error) or attempt == 3:
                            raise
                        print(json.dumps({'code': code, 'retry_empty_service_response': attempt + 1}), flush=True)
                        time.sleep(2)
        elif code == 'hmn':
            sys.path.insert(0, '/workspace/restored-mustang/work/episode-005-atacama/hmong-1.6.6')
            os.environ.update(HMOOB_DEVICE='cpu', HMOOB_PRECISION='fp32', HMOOB_MODEL_DIR='/workspace/restored-mustang/work/episode-010-mustang/hmong-models')
            from hmong_native_models import verify_models
            from hmong_native import SpeechEngine
            verify_models()
            engine = SpeechEngine()
            reference = Path('/workspace/restored-mustang/work/episode-005-atacama/hmong-1.6.6/assets/hmong/female-3.wav')
            assert sha(reference) == profile['reference_sha256']
            def speak(text, path):
                samples, rate = engine.synthesize(text, str(reference), '', speed=1., quality='fast', audio_profile='clear-v1')
                sf.write(path, samples, rate, subtype='FLOAT')
        else:
            if voice.startswith('piper:'):
                from fast_backend import handle
            else:
                from multilingual_backend import handle
            def speak(text, path): return handle({'op': 'render', 'language': profile['melo_language'], 'voice': voice, 'text': text, 'threads': 1, 'output': str(path)})
        cache = ROOT / 'scratch' / code
        cache.mkdir(parents=True, exist_ok=True)
        blocked = []
        for row in rows:
            n, text = row['scene'], row.get('voice_text', row['text'])
            key = hashlib.sha256((voice + profile['engine'] + text + str(row['duration_seconds'])).encode()).hexdigest()
            raw, fitted = cache / f'{n:03d}-raw.wav', cache / f'{n:03d}-fit.wav'
            stamp = cache / f'{n:03d}.sha256'
            if not raw.exists() or not stamp.exists() or stamp.read_text() != key:
                speak(text, raw)
                stamp.write_text(key)
                fitted.unlink(missing_ok=True)
            samples, rate = sf.read(raw, dtype='float32')
            assert samples.ndim == 1 and samples.size and np.isfinite(samples).all()
            active = np.flatnonzero(np.abs(samples) > 0.00001)
            assert active.size, f'{code} cue {n}: silent waveform'
            start = max(0, int(active[0]) - int(rate * .15))
            end = min(len(samples), int(active[-1]) + int(rate * .15) + 1)
            duration = (end - start) / rate
            slot = row['duration_seconds']
            tempo = max(.9, duration / (slot - .35))
            segment = {'scene': n, 'text': text, 'raw_seconds': len(samples) / rate,
                       'speech_window_seconds': duration, 'tempo': tempo, 'word_truncation': False}
            if tempo > 1.5:
                blocked.append(n)
                segment['needs_shorter_localization'] = True
            else:
                if not fitted.exists():
                    run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(raw), '-af',
                         f'atrim=start_sample={start}:end_sample={end},asetpts=PTS-STARTPTS,atempo={tempo:.9f},apad',
                         '-t', str(slot), '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le', str(fitted)])
                with wave.open(str(fitted)) as audio: assert audio.getnframes() == slot * 24000
                segment['fitted_seconds'] = slot
            report['segments'].append(segment)
            save(report_file, report)
            if n % 15 == 0: print(json.dumps({'code': code, 'cues': n, 'needs_shorter': blocked}), flush=True)
        if blocked:
            report.update(status='needs_shorter_localization', needs_shorter_cues=blocked)
            save(report_file, report)
            raise RuntimeError('Localize overlong cues before completing audio: ' + str(blocked))
        joined = cache / 'joined.wav'
        with wave.open(str(joined), 'wb') as output:
            output.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
            for n in range(1, 130):
                with wave.open(str(cache / f'{n:03d}-fit.wav')) as part:
                    output.writeframesraw(part.readframes(part.getnframes()))
            output.writeframesraw(b'\x00' * (2 * 24000 * 2))
        flac = ROOT / 'audio' / f'voice-{code}-21m32s.flac'
        mp3 = ROOT / 'audio' / f'voice-{code}-21m32s.mp3'
        measurement = run(['ffmpeg', '-nostdin', '-hide_banner', '-i', str(joined), '-af',
                           'loudnorm=I=-18:TP=-2:LRA=7:print_format=json', '-f', 'null', '-'])
        loud = json.JSONDecoder().raw_decode(measurement.stderr[measurement.stderr.rfind('{'):])[0]
        normalization = ('loudnorm=I=-18:TP=-2:LRA=7:linear=true:'
                         f"measured_I={loud['input_i']}:measured_TP={loud['input_tp']}:"
                         f"measured_LRA={loud['input_lra']}:measured_thresh={loud['input_thresh']}:offset={loud['target_offset']}")
        run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(joined), '-af', normalization,
             '-ar', '24000', '-ac', '1', '-c:a', 'flac', '-sample_fmt', 's16', str(flac)])
        run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(flac), '-ar', '24000', '-ac', '1', '-b:a', '96k', str(mp3)])
        info = sf.info(flac)
        assert info.frames == 31008000 and info.samplerate == 24000
        decoded = subprocess.Popen(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(mp3), '-f', 's16le', '-ar', '24000', '-ac', '1', 'pipe:1'], stdout=subprocess.PIPE)
        count = 0
        while block := decoded.stdout.read(1024 * 1024): count += len(block)
        assert decoded.wait() == 0 and count == 62016000
        report.update(status='created_pending_listening_review', decoded_seconds=1292,
                      decoded_samples=31008000, sample_rate=24000, channels=1,
                      mp3=mp3.name, flac=flac.name, mp3_sha256=sha(mp3), flac_sha256=sha(flac))
        save(report_file, report)
        print(json.dumps({'code': code, 'status': report['status'], 'seconds': 1292}), flush=True)
    except Exception as error:
        if report['status'] != 'needs_shorter_localization':
            report.update(status='blocked_or_failed', error=str(error)[:500])
            save(report_file, report)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('codes', nargs='+')
    parser.add_argument('--allow-online', action='store_true')
    args = parser.parse_args()
    failures = []
    for code in args.codes:
        try: render(code, args.allow_online)
        except Exception as error:
            failures.append(code)
            print(json.dumps({'code': code, 'error': str(error)[:500]}), flush=True)
    sys.exit(1 if failures else 0)
