"""Compare real CPU Turbo teams with identical text, voice and FP32 sampling."""
import argparse
import json
import os
from pathlib import Path
import statistics
import sys
import time
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = args.data.resolve()
    os.environ.update(VOICE_STUDIO_DATA_DIR=str(data), HF_HOME=str(data/'models/cache'),
                      HF_HUB_CACHE=str(data/'models/cache/hub'), HF_HUB_OFFLINE='1',
                      TRANSFORMERS_OFFLINE='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'app'))
    import worker
    from performance import speed_report
    for folder in ('audio', 'parts', 'jobs'):
        (data/folder).mkdir(exist_ok=True)
    text = '\n'.join([
        'Hôm nay trời nắng đẹp và có gió nhẹ.',
        'Một câu chuyện hay mang đến nhiều cảm xúc.',
        'Chúng ta cùng bước đi trên con đường nhỏ.',
        'Giọng đọc rõ ràng giúp người nghe dễ hiểu.',
    ] * 6)
    trials = []
    for round_index in range(3):
        cases = [('original', 2, 2), ('compact', 4, 1)]
        if round_index % 2: cases.reverse()
        for name, workers, threads in cases:
            worker.close_nano_pool()
            for phase in ('cold', 'warm'):
                ident = 'compact-bench-' + uuid.uuid4().hex
                job = {'id': ident, 'text': text, 'engine': 'vieneu', 'voice_id': 'vi-maianh',
                       'speaker': 'Mai Anh', 'language': 'vi', 'format': 'wav', 'input_format': 'txt',
                       'quality': 'standard', 'speed': 1, 'delivery': 'natural', 'paragraph_pause': 0,
                       'model_memory': 'shared', 'nano_parallel': workers, 'nano_threads': threads,
                       'render_mode': 'balanced', 'resource_profile': 'smooth',
                       'audio_fit_backend': 'ffmpeg', 'segment_plan': 'classic-v1'}
                started = time.perf_counter()
                worker.render(job)
                elapsed = time.perf_counter() - started
                result = json.loads((data/'parts'/ident/'result.json').read_text())
                assert result['completed'] == result['total'] == 24
                assert not result.get('duration_limited')
                record = {'mode': name, 'round': round_index+1, 'phase': phase,
                          'execution': result['execution_settings'],
                          'report': speed_report(result['audio_seconds'], elapsed, result['spoken_audio_seconds'])}
                trials.append(record)
                print(json.dumps(record), flush=True)
    worker.close_nano_pool()
    medians = {name: statistics.median(t['report']['realtime_multiplier'] for t in trials
                if t['mode'] == name and t['phase'] == 'warm') for name in ('original', 'compact')}
    report = {'platform': sys.platform, 'public_voice': 'Mai Anh', 'private_voices_tested': False,
              'engine': 'vieneu', 'precision': 'fp32', 'text': text, 'text_unchanged': True,
              'speech_playback_speed': 1, 'quality_and_sampling_unchanged': True,
              'trials': trials, 'warm_median_throughput': medians,
              'relative_throughput': medians['compact']/medians['original'],
              'windows_tested': False, 'gpu_tested': False, 'target_30x_verified': False}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
