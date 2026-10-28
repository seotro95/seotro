"""Native offline process/shared comparison through the production renderer.

Every case runs in a fresh bundled interpreter. Measurements include the same
public script, actual output speech and peak process-tree RSS; they do not
certify a complete hour or a 30x result on another machine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time


# Multiprocessing spawn imports this module too. Keep the deterministic Nano
# benchmark seed local to this QA process, without changing installed SDK files.
if os.environ.get('VOICE_STUDIO_QA_APP'):
    sys.path.insert(0, os.environ['VOICE_STUDIO_QA_APP'])
    from vieneu.v3nano import V3NanoVieNeuTTS
    _original_infer = V3NanoVieNeuTTS.infer
    def _seeded_nano(self, text, *args, **kwargs):
        kwargs.setdefault('seed', int.from_bytes(hashlib.sha256(text.encode()).digest()[:4], 'little'))
        return _original_infer(self, text, *args, **kwargs)
    V3NanoVieNeuTTS.infer = _seeded_nano


TEXT = '\n'.join((
    'Trời hôm nay rất đẹp, nắng trải trên con đường nhỏ.',
    'Cô bé mở cửa sổ và lắng nghe tiếng chim hót.',
    'Mẹ đang pha ấm trà thơm trong căn bếp.',
    'Cả nhà cùng ngồi xuống và kể chuyện.',
    'Một cuốn sách hay mở ra những điều mới.',
    'Ngoài sân, những bông hoa vừa nở.',
))
SRT = ('1\n00:00:00,250 --> 00:00:01,150\nXin chào.\n\n'
       '2\n00:00:01,500 --> 00:00:02,750\nCảm ơn.')


def run_case(root, engine, memory, output):
    import psutil
    import soundfile as sf
    import onnxruntime as ort
    import worker
    from narration import plan_segments
    from performance import speed_report
    from subtitles import parse_srt

    data = root/'app/.data'
    job = {'engine': engine, 'speaker': 'Minh Quân' if engine == 'vieneu_nano' else 'Mai Anh',
           'voice_id': 'public-portable-qa', 'language': 'vi', 'text': TEXT,
           'input_format': 'txt', 'format': 'wav', 'quality': 'standard',
           'speed': 1, 'delivery': 'natural', 'paragraph_pause': 0,
           'nano_steps': 4, 'nano_parallel': 2, 'nano_threads': 1,
           'audio_fit_backend': 'wsola', 'cue_fit': 'auto', 'max_cue_tempo': 1.5,
           'resource_profile': 'maximum', 'model_memory': memory}
    expected = sum(bool(segment.text) for segment in plan_segments(job))
    model_ids, engine_ids, lock_ids, session_sets = set(), set(), set(), []
    audit_lock = threading.Lock()
    if memory == 'shared':
        import shared_synthesis
        acquire = shared_synthesis.acquire_model
        def audited_acquire(key, factory):
            model = acquire(key, factory)
            sessions = {name:id(value) for name,value in vars(model.engine).items()
                        if isinstance(value, ort.InferenceSession)}
            with audit_lock:
                model_ids.add(id(model)); engine_ids.add(id(model.engine))
                lock_ids.add(id(model.engine._lock)); session_sets.append(sessions)
            return model
        shared_synthesis.acquire_model = audited_acquire
    process = psutil.Process()
    stop = threading.Event()
    peak = [0]
    def watch():
        while not stop.is_set():
            try:
                processes = [process, *process.children(recursive=True)]
                peak[0] = max(peak[0], sum(item.memory_info().rss for item in processes if item.is_running()))
            except psutil.Error:
                pass
            stop.wait(.025)
    monitor = threading.Thread(target=watch, daemon=True)
    monitor.start()
    measurements = []
    try:
        for phase in ('cold', 'warm'):
            measured = {**job, 'id': 'qa-v19-'+engine+'-'+memory+'-'+phase}
            assert not (data/'parts'/measured['id']).exists(), 'QA must not reuse chunk checkpoints'
            started = time.perf_counter()
            worker.render(measured)
            wall = time.perf_counter()-started
            result = json.loads((data/'parts'/measured['id']/'result.json').read_text(encoding='utf-8'))
            info = sf.info(data/'audio'/(measured['id']+'.wav'))
            assert result['completed'] == expected == result['total']
            assert not result['duration_limited'] and info.frames > 24000
            settings = result['execution_settings']
            assert settings['engine'] == engine and settings['workers'] == 2
            assert settings['threads'] == 1 and settings['model_memory'] == memory
            if engine == 'vieneu':assert settings['precision'] == 'fp32'
            measurements.append({'phase': phase, 'includes_initial_model_load': phase == 'cold',
                'peak_process_tree_rss_bytes': peak[0], 'output_frames': info.frames,
                'output_pcm_sha256': hashlib.sha256(sf.read(data/'audio'/(measured['id']+'.wav'), dtype='int16')[0].tobytes()).hexdigest(),
                'execution_settings': settings, **speed_report(info.duration, wall, result['spoken_audio_seconds'])})
        timed = {**job, 'id': 'qa-v19-'+engine+'-'+memory+'-srt', 'text': SRT, 'input_format': 'srt'}
        worker.render(timed)
        alignment = json.loads((data/'parts'/timed['id']/'alignment.json').read_text(encoding='utf-8'))
        assert alignment['sync_ok'] and len(alignment['cues']) == 2
        assert sf.info(data/'audio'/(timed['id']+'.wav')).frames == 66000
        assert parse_srt((data/'audio'/(timed['id']+'.srt')).read_text(encoding='utf-8')) == parse_srt(SRT)
    finally:
        worker.close_nano_pool()
        stop.set()
        monitor.join(timeout=2)
    report = {'engine': engine, 'model_memory': memory, 'workers': 2, 'threads_per_worker': 1,
              'input_sha256': hashlib.sha256(TEXT.encode()).hexdigest(),
              'measurements': measurements, 'srt_cue_count': 2, 'srt_exact_frames': 66000,
              'srt_original_text_and_clocks_preserved': True}
    if memory == 'shared':
        assert len(model_ids) >= 2 and len(engine_ids) >= 2 and len(lock_ids) >= 2
        assert session_sets and len(session_sets[0]) >= 4
        assert all(sessions == session_sets[0] for sessions in session_sets)
        report['shared_session_audit'] = {'distinct_model_copies': len(model_ids),
            'distinct_engine_copies': len(engine_ids), 'distinct_decode_locks': len(lock_ids),
            'shared_session_count': len(session_sets[0]), 'same_onnx_session_objects': True}
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--engine', choices=('vieneu_nano', 'vieneu'))
    parser.add_argument('--memory', choices=('process', 'shared'))
    args = parser.parse_args()
    root = args.root.resolve()
    assert os.name == 'nt', 'Native Windows comparison must run on Windows'
    assert Path(sys.executable).resolve().parent == root/'runtime', 'Use the relocated bundled interpreter'
    assert os.environ.get('HF_HUB_OFFLINE') == '1' and os.environ.get('TRANSFORMERS_OFFLINE') == '1'
    if args.engine:
        assert args.memory
        run_case(root, args.engine, args.memory, args.output)
        return
    import psutil
    records = []
    for engine in ('vieneu_nano', 'vieneu'):
        for memory in ('process', 'shared'):
            destination = args.output.with_name(args.output.stem+'-'+engine+'-'+memory+'.json')
            env = dict(os.environ, VOICE_STUDIO_QA_APP=str(root/'app'),
                       OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', OMP_NUM_THREADS='1')
            subprocess.run([sys.executable, '-s', '-X', 'utf8', str(Path(__file__).resolve()),
                            str(root), '--output', str(destination), '--engine', engine, '--memory', memory],
                           env=env, cwd=root, check=True, timeout=480)
            records.append(json.loads(destination.read_text(encoding='utf-8')))
            destination.unlink()
    nano = [record for record in records if record['engine'] == 'vieneu_nano']
    assert [[phase['output_frames'] for phase in item['measurements']] for item in nano][0] == \
           [[phase['output_frames'] for phase in item['measurements']] for item in nano][1]
    report = {'format': 'voice-studio-shared-native-qa-v1', 'version': '1.9.0',
              'platform': 'native-windows-x64', 'measurements': records,
              'nano_seed_method': 'Benchmark-only deterministic per-text seed; installed SDK files unchanged',
              'turbo_sampling': 'Production stochastic sampling; durations may differ between jobs',
              'rss_method': 'Peak sum of parent and descendant working-set RSS sampled every25ms; shared OS pages may be counted more than once across processes',
              'runtime_psutil_version': psutil.__version__, 'complete_hour_measured': False,
              'private_voice_samples_used': False, 'target_30x_guaranteed': False,
              'limitations': ['Short public scripts only', 'The runner is not the user computer',
                              'Compare actual generated speech per wall time; subtitle gaps do not count as speech']}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Native production shared/process comparison passed: '+str(args.output), flush=True)


if __name__ == '__main__':
    main()
