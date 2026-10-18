"""Required native Windows checks, run with relocated bundled Python offline."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid
import wave


def main():
    root = Path(sys.argv[1]).resolve()
    app = root/'app'
    assert os.name == 'nt', 'A Windows bundle must be tested on Windows'
    assert Path(sys.executable).resolve().parent == root/'runtime', 'Use bundled Python'
    assert Path(sys.prefix).resolve() == root/'runtime', 'Python must be relocatable'
    assert os.environ.get('HF_HUB_OFFLINE') == '1'
    assert os.environ.get('TRANSFORMERS_OFFLINE') == '1'
    sys.path.insert(0, str(app))
    import numpy as np
    import onnxruntime
    import soundfile as sf
    import httpx
    from fastapi.testclient import TestClient
    import app as studio
    from worker import render
    from subtitles import parse_srt
    for module in (np, onnxruntime, sf, httpx):
        assert root/'runtime' in Path(module.__file__).resolve().parents, 'Dependency escaped bundled runtime'
    for binary in ('ffmpeg', 'ffprobe'):
        assert Path(shutil.which(binary)).resolve().parent == root/'ffmpeg/bin'
        subprocess.run([binary, '-version'], check=True, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, '-m', 'pip', 'check'], check=True)
    data = app/'.data'
    with TestClient(studio.app) as client:
        config = client.get('/api/config').json()
        assert config['edition'] == 'standalone-voice' and config['version'] == '1.3.0'
        assert config['nano_ready'] and config['max_characters'] == 1000000
        assert client.get('/').status_code == 200
        assert client.get('/static/app.js').status_code == 200
        voices = client.get('/api/voices').json()['voices']
        assert any(item['engine'] == 'vieneu_nano' and item['ready'] for item in voices)
    engines = [('vieneu_nano', 'Minh Quân')]
    if (data/'models/vieneu.ready').exists():
        engines.append(('vieneu', 'Mai Anh'))
    for engine, speaker in engines:
        job = {'id': 'portable-real-'+engine, 'text': 'Xin chào, đây là bản kiểm tra giọng nói tiếng Việt.',
               'engine': engine, 'speaker': speaker, 'voice_id': 'check', 'language': 'vi',
               'quality': 'standard', 'format': 'wav', 'speed': 1, 'nano_steps': 16,
               'nano_threads': 2, 'paragraph_pause': 0}
        render(job)
        samples, rate = sf.read(data/'audio'/(job['id']+'.wav'))
        assert rate == 24000 and len(samples) > rate*.3 and np.max(np.abs(samples)) > .001
    # Real bundled Nano speech is fitted into an original 900 ms subtitle slot.
    real_srt = '1\n00:00:00,250 --> 00:00:01,150\nXin chào.'
    real = dict(job, id='portable-real-srt', engine='vieneu_nano', speaker='Minh Quân',
                input_format='srt', cue_fit='auto', max_cue_tempo=1.5, text=real_srt)
    render(real)
    info = sf.info(data/'audio/portable-real-srt.wav')
    assert info.frames == round(1.15*24000)
    report = json.loads((data/'parts/portable-real-srt/alignment.json').read_text(encoding='utf-8'))
    assert report['sync_ok'] and report['cues'][0]['spoken_start'] == .25
    # Reproduce the exact reported failure: complete 1.410 s source -> 0.900 s
    # slot. Two tones distinguish source beginning/tail and detect truncation.
    def synthesize(text, output):
        chunks = []
        for frequency in (220, 440):
            clock = np.arange(round(.705*24000))/24000
            chunks.append((6000*np.sin(2*np.pi*frequency*clock)).astype('<i2'))
        with wave.open(str(output), 'wb') as target:
            target.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
            target.writeframes(np.concatenate(chunks).tobytes())
    regression = dict(real, id='portable-reported-1410-900', engine='system',
                      text='1\n00:00:00,250 --> 00:00:01,150\nMột câu cần căn thời gian.')
    render(regression, synthesize)
    samples, rate = sf.read(data/'audio/portable-reported-1410-900.wav')
    assert len(samples) == round(1.15*rate)
    assert not np.any(samples[:round(.25*rate)])
    cue = samples[round(.25*rate):]
    def pitch(window):
        return np.fft.rfftfreq(len(window), 1/rate)[np.argmax(abs(np.fft.rfft(window*np.hanning(len(window)))))]
    assert abs(pitch(cue[round(.08*rate):round(.25*rate)])-220) < 15
    assert abs(pitch(cue[round(.58*rate):round(.75*rate)])-440) < 15
    report = json.loads((data/'parts/portable-reported-1410-900/alignment.json').read_text(encoding='utf-8'))
    assert report['sync_ok'] and report['cues'][0]['tempo'] > 1.5
    assert parse_srt((data/'audio/portable-reported-1410-900.srt').read_text(encoding='utf-8')) == parse_srt(regression['text'])
    # Exercise user download endpoints, including conversion with bundled FFmpeg.
    export_id = uuid.uuid4().hex
    for suffix in ('wav', 'srt'):
        shutil.copy2(data/'audio'/('portable-real-srt.'+suffix), data/'audio'/(export_id+'.'+suffix))
    (data/'jobs'/(export_id+'.json')).write_text(json.dumps({'id': export_id, 'status': 'done', 'format': 'wav'}), encoding='utf-8')
    with TestClient(studio.app) as client:
        for suffix in ('wav', 'mp3', 'txt', 'srt'):
            response = client.get(f'/api/jobs/{export_id}/export.{suffix}')
            assert response.status_code == 200 and len(response.content) > 10, 'Export failed: '+suffix
    # Invoke the real bundled launcher and make an actual loopback HTTP request.
    log = root/'portable-launch-check.log'
    with log.open('wb') as output:
        process = subprocess.Popen([sys.executable, str(app/'launcher.py'), '--no-browser'], cwd=root,
                                   stdout=output, stderr=subprocess.STDOUT)
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            ready = False
            for _ in range(120):
                if process.poll() is not None:
                    raise RuntimeError('Bundled launcher exited: '+log.read_text(encoding='utf-8', errors='replace'))
                for port in range(8770, 8790):
                    try:
                        with opener.open(f'http://127.0.0.1:{port}/api/config', timeout=.1) as response:
                            config = json.load(response)
                        if config.get('edition') == 'standalone-voice' and config.get('nano_ready'):
                            ready = True
                            break
                    except (OSError, ValueError):
                        pass
                if ready:
                    break
                time.sleep(.25)
            assert ready, 'Packaged launcher did not expose its local API'
        finally:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            process.wait(timeout=30)
    log.unlink()
    print('PASS: relocated Windows Python, local packages, bundled offline Nano/Turbo, 1.410s→0.900s SRT, pitch/tail, FFmpeg and actual launcher HTTP.', flush=True)


if __name__ == '__main__':
    main()
