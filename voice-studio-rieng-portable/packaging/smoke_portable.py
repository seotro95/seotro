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
    import psutil
    from fastapi.testclient import TestClient
    import app as studio
    from worker import render, close_nano_pool
    from narration import plan_segments
    from performance import speed_report
    from subtitles import parse_srt
    for module in (np, onnxruntime, sf, httpx, psutil):
        assert root/'runtime' in Path(module.__file__).resolve().parents, 'Dependency escaped bundled runtime'
    for binary in ('ffmpeg', 'ffprobe'):
        assert Path(shutil.which(binary)).resolve().parent == root/'ffmpeg/bin'
        subprocess.run([binary, '-version'], check=True, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, '-m', 'pip', 'check'], check=True)
    data = app/'.data'
    with TestClient(studio.app) as client:
        config = client.get('/api/config').json()
        assert config['edition'] == 'standalone-voice' and config['version'] == '1.9.0'
        assert config['nano_ready'] and config['max_characters'] == 1000000
        assert len(config['delivery_profiles']) == 10
        assert set(config['rendering_presets']) == {'fast', 'balanced', 'quality'}
        assert set(config['rendering_presets_by_resource']) == {'maximum', 'smooth', 'light'}
        hardware_response = client.get('/api/system-info')
        assert hardware_response.status_code == 200
        hardware = hardware_response.json()
        assert hardware['logical_cores'] >= 1 and hardware['cpu']
        assert hardware['physical_cores'] >= 1 and hardware['ram_gb'] > 1, 'CPU/RAM detection is required for automatic parallelism'
        assert client.get('/').status_code == 200
        assert client.get('/static/app.js').status_code == 200
        voices = client.get('/api/voices').json()['voices']
        assert any(item['engine'] == 'vieneu_nano' and item['ready'] for item in voices)
        assert len([item for item in voices if item['engine'] == 'vieneu_nano']) >= 11
        assert len([item for item in voices if item['engine'] == 'vieneu']) >= 25
    engines = [('vieneu_nano', 'Minh Quân')]
    if (data/'models/vieneu.ready').exists():
        engines.append(('vieneu', 'Mai Anh'))
    for engine, speaker in engines:
        job = {'id': 'portable-real-'+engine, 'text': 'Xin chào, đây là bản kiểm tra giọng nói tiếng Việt.',
               'engine': engine, 'speaker': speaker, 'voice_id': 'check', 'language': 'vi',
               'quality': 'standard', 'format': 'wav', 'speed': 1, 'nano_steps': 16,
               'nano_threads': 2, 'paragraph_pause': 0, 'model_memory': 'shared',
               'resource_profile': 'maximum'}
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
    # The opt-in fast fitter must preserve the same clock, pitch and full tail.
    wsola_job = dict(regression, id='portable-wsola-1410-900', audio_fit_backend='wsola')
    render(wsola_job, synthesize)
    fast_samples, fast_rate = sf.read(data/'audio/portable-wsola-1410-900.wav')
    assert fast_rate == rate and len(fast_samples) == round(1.15*rate)
    assert not np.any(fast_samples[:round(.25*rate)])
    fast_cue = fast_samples[round(.25*rate):]
    assert abs(pitch(fast_cue[round(.08*rate):round(.25*rate)])-220) < 15
    assert abs(pitch(fast_cue[round(.58*rate):round(.75*rate)])-440) < 15
    fast_report = json.loads((data/'parts/portable-wsola-1410-900/alignment.json').read_text(encoding='utf-8'))
    assert fast_report['sync_ok'] and fast_report['cues'][0]['spoken_end'] <= 1.15
    assert parse_srt((data/'audio/portable-wsola-1410-900.srt').read_text(encoding='utf-8')) == parse_srt(regression['text'])
    # Native Nano duration control (news=1.04) plus the actual fast SRT backend.
    paced = dict(real, id='portable-native-news-wsola', delivery='news', audio_fit_backend='wsola', nano_steps=4)
    render(paced)
    assert sf.info(data/'audio/portable-native-news-wsola.wav').frames == round(1.15*24000)
    paced_report = json.loads((data/'parts/portable-native-news-wsola/alignment.json').read_text(encoding='utf-8'))
    assert paced_report['sync_ok']
    # Mai Anh/Turbo must use the shared bounded path, keep its reference
    # voice/FP32 and preserve two original subtitle clocks in ordered assembly.
    if (data/'models/vieneu.ready').exists():
        turbo_srt='1\n00:00:00,250 --> 00:00:01,150\nXin chào.\n\n2\n00:00:01,500 --> 00:00:02,750\nCảm ơn.'
        turbo_job=dict(real,id='portable-turbo-parallel-srt',engine='vieneu',speaker='Mai Anh',quality='standard',
                       text=turbo_srt,nano_parallel=2,nano_threads=1,audio_fit_backend='wsola')
        render(turbo_job)
        turbo_result=json.loads((data/'parts'/turbo_job['id']/'result.json').read_text(encoding='utf-8'))
        assert turbo_result['execution_settings']['engine']=='vieneu'
        assert turbo_result['execution_settings']['workers']==2 and turbo_result['execution_settings']['precision']=='fp32'
        assert turbo_result['execution_settings']['model_memory']=='shared'
        assert sf.info(data/'audio'/(turbo_job['id']+'.wav')).frames==round(2.75*24000)
        assert parse_srt((data/'audio'/(turbo_job['id']+'.srt')).read_text(encoding='utf-8'))==parse_srt(turbo_srt)
    # Two fresh jobs distinguish cold model setup from reusable warm
    # workers. Distinct sentences cannot reuse chunk checkpoints. No artificial
    # paragraph gaps or subtitle silence inflate speech throughput.
    benchmark_text = '\n'.join([
        'Bản tin sáng nay ghi nhận nhiều thay đổi tích cực trong đời sống của người dân thành phố.',
        'Trên con đường nhỏ, các bạn học sinh cùng bước đến trường trong không khí vui tươi.',
        'Những người làm vườn chăm sóc từng luống rau để chuẩn bị cho phiên chợ cuối tuần.',
        'Một cuốn sách hay có thể mở ra nhiều cách nhìn mới về thế giới rộng lớn quanh ta.',
        'Cô hướng dẫn viên kể lại câu chuyện lịch sử bằng giọng nói rõ ràng và những chi tiết sinh động.',
        'Trong căn phòng yên tĩnh, người nghệ sĩ đang hoàn thiện bức tranh về quê hương của mình.',
        'Đội tình nguyện đã dành buổi chiều để trồng thêm cây xanh dọc hai bên đường làng.',
        'Khi chuẩn bị một hành trình mới, chúng ta cần kiểm tra hành lý và ghi nhớ những lời dặn.',
        'Tiếng sóng biển hòa cùng làn gió nhẹ khiến mọi người cảm thấy thư thái sau ngày làm việc.',
        'Những thông tin vừa đọc chỉ là đoạn thử công khai để đo tốc độ tạo giọng trên máy này.',
    ])
    fast_job = dict(real, id='portable-fast-cold', text=benchmark_text, input_format='txt',
                    speaker='Ái Hân', delivery='news', speed=1, nano_steps=4, nano_parallel=2,
                    nano_threads=2, paragraph_pause=0, render_mode='fast', audio_fit_backend='wsola',
                    segment_plan='nano-packed-v1')
    segment_count = len(plan_segments(fast_job))
    assert 8 <= segment_count <= 12
    measurements = []
    close_nano_pool()
    try:
        for phase in ('cold', 'warm'):
            measured_job = dict(fast_job, id='portable-fast-'+phase)
            started = time.perf_counter()
            render(measured_job)
            wall_seconds = time.perf_counter()-started
            result = json.loads((data/'parts'/measured_job['id']/'result.json').read_text(encoding='utf-8'))
            assert result['completed'] == segment_count and not result['duration_limited']
            info = sf.info(data/'audio'/(measured_job['id']+'.wav'))
            assert info.frames > 24000 and result['spoken_audio_seconds'] > 1
            assert result['execution_settings']['model_memory']=='shared'
            measurements.append({'phase': phase, 'includes_process_model_setup': phase == 'cold',
                                 **speed_report(info.duration, wall_seconds, result['spoken_audio_seconds'])})
    finally:
        close_nano_pool()
    qa = {'platform': 'native-windows-x64', 'estimate_only': True,
          'runner_hardware': {key: hardware.get(key) for key in ('cpu', 'physical_cores', 'logical_cores', 'ram_gb')},
          'runtime_psutil_version': psutil.__version__,
          'fast_sample': {'engine': 'vieneu_nano', 'speaker': 'Ái Hân', 'steps': 4, 'parallel': 2,
                          'threads_per_worker': 2, 'genre': 'news', 'native_speed': 1.04,
                          'segments': segment_count, 'paragraph_pause': 0, 'measurements': measurements},
          'target_30x_guaranteed': False,
          'checks': ['offline shared-model Nano and Turbo', 'real native news pacing', 'FFmpeg and WSOLA clock/pitch/tail', 'WAV MP3 TXT SRT exports', 'launcher HTTP']}
    print('PORTABLE_BENCHMARK '+json.dumps(qa['fast_sample'], ensure_ascii=False), flush=True)
    # Exercise user download endpoints, including conversion with bundled FFmpeg.
    export_id = uuid.uuid4().hex
    for suffix in ('wav', 'srt'):
        shutil.copy2(data/'audio'/('portable-real-srt.'+suffix), data/'audio'/(export_id+'.'+suffix))
    (data/'jobs'/(export_id+'.json')).write_text(json.dumps({'id': export_id, 'status': 'done', 'format': 'wav'}), encoding='utf-8')
    with TestClient(studio.app) as client:
        for suffix in ('wav', 'mp3', 'txt', 'srt'):
            response = client.get(f'/api/jobs/{export_id}/export.{suffix}')
            assert response.status_code == 200 and len(response.content) > 10, 'Export failed: '+suffix
        # Exercise the actual HTTP queue and persistent worker's calibration
        # dispatch. Every candidate uses real bundled Nano inference offline.
        response = client.post('/api/calibrate', json={'voice_id': 'nano-minhquan', 'render_mode': 'fast'})
        assert response.status_code == 202, response.text
        ident = response.json()['id']
        deadline = time.monotonic()+600
        while time.monotonic() < deadline:
            measured = client.get('/api/jobs/'+ident).json()
            if measured['status'] in {'done', 'error', 'cancelled'}:
                break
            time.sleep(.25)
        assert measured['status'] == 'done', measured
        calibration = measured['calibration_report']
        assert measured.get('speed_report') is None, 'Total calibration time is not synthesis throughput'
        assert calibration['nano_steps'] == 4 and calibration['estimate_only']
        selected = calibration['selected']
        assert selected['warm']['measurement_audio_seconds'] > 10
        assert len(calibration['candidates']) >= 1
        assert not list((data/'parts').glob(ident+'-measure-*'))
        assert not list((data/'audio').glob(ident+'-measure-*'))
        saved = client.get('/api/config').json()['rendering_presets']['fast']
        assert all(saved[key] == value for key, value in selected['settings'].items())
        assert client.get('/api/audio/'+ident).status_code == 200
        # The next new job must render with the saved team without checkpoint
        # reuse. It exercises persistent warm workers after calibration.
        response = client.post('/api/benchmark', json={'voice_id': 'nano-minhquan', 'render_mode': 'fast'})
        assert response.status_code == 202, response.text
        follow_id = response.json()['id']
        deadline = time.monotonic()+180
        while time.monotonic() < deadline:
            follow = client.get('/api/jobs/'+follow_id).json()
            if follow['status'] in {'done', 'error', 'cancelled'}:
                break
            time.sleep(.25)
        assert follow['status'] == 'done' and follow['speed_report']['measurement_audio_seconds'] > 10, follow
        assert follow['nano_parallel'] == selected['settings']['nano_parallel']
        qa['machine_calibration'] = calibration
        qa['post_calibration_benchmark'] = follow['speed_report']
        qa['checks'].append('real HTTP calibration, saved presets, warm next job and temporary-output cleanup')
        if (data/'models/vieneu.ready').exists():
            turbo_measurements=[]
            for phase in ('cold','warm'):
                response=client.post('/api/benchmark',json={'voice_id':'vi-maianh','render_mode':'fast',
                                  'nano_parallel':2,'nano_threads':1,'quality':'standard'})
                assert response.status_code==202,response.text
                turbo_id=response.json()['id']
                deadline=time.monotonic()+180
                while time.monotonic()<deadline:
                    turbo=client.get('/api/jobs/'+turbo_id).json()
                    if turbo['status'] in {'done','error','cancelled'}:break
                    time.sleep(.25)
                assert turbo['status']=='done',turbo
                assert turbo['speaker']=='Mai Anh' and turbo['engine']=='vieneu'
                assert turbo['execution_settings']['workers']==2 and turbo['execution_settings']['threads']==1
                assert turbo['execution_settings']['precision']=='fp32' and turbo['speed_report']['measurement_audio_seconds']>10
                assert turbo['execution_settings']['model_memory']=='shared'
                turbo_measurements.append({'phase':phase,**turbo['speed_report']})
            qa['turbo_sample']={'engine':'vieneu','speaker':'Mai Anh','precision':'fp32',
                               'parallel':2,'threads_per_worker':1,'blas_threads':1,'measurements':turbo_measurements}
            qa['checks'].append('real Mai Anh FP32 parallel SRT and cold/warm HTTP benchmark')
    (root/'PORTABLE-QA.json').write_text(json.dumps(qa, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
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
    try:
        main()
    finally:
        worker = sys.modules.get('worker')
        if worker is not None:
            worker.close_nano_pool()
