"""Create short real French/Japanese samples using a public reference only."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
import wave


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-dir', required=True, type=Path)
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--reference', required=True, type=Path)
    parser.add_argument('--reference-text', required=True, type=Path)
    parser.add_argument('--asr-reference', type=Path,
                        help='Public English WAV used to check the missing-transcript route')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    os.environ.update(VOICE_STUDIO_DATA_DIR=str(args.data_dir.resolve()), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    sys.path.insert(0, str(args.app_dir.resolve()))
    import fast_multilingual
    import numpy as np
    import soundfile as sf
    args.output.parent.mkdir(parents=True, exist_ok=True)
    audio_directory = args.data_dir.resolve() / 'qa-audio'
    audio_directory.mkdir(parents=True, exist_ok=True)
    samples = []
    asr_check = None
    public_transcript = args.reference_text.read_text(encoding='utf-8').strip()
    try:
        for index, (language, text) in enumerate([
            ('fr', 'Bonjour. Cette phrase vérifie la lecture en français.'),
            ('ja', 'こんにちは。これは日本語の音声テストです。'),
            ('fr', 'Le modèle reste chargé pour la phrase suivante.'),
        ]):
            synthesize = fast_multilingual.create_synthesizer(
                args.reference.resolve(), args.data_dir.resolve(), threads=4,
                steps=16, device='cpu', language=language, reference_text=public_transcript)
            audio = audio_directory / f'native-public-{index}-{language}.wav'
            start = time.monotonic()
            synthesize(text, audio)
            elapsed = time.monotonic() - start
            with wave.open(str(audio)) as source:
                assert (source.getnchannels(), source.getsampwidth(), source.getframerate()) == (1, 2, 24000)
                duration = source.getnframes() / source.getframerate()
            values, rate = sf.read(audio, dtype='float32')
            assert duration >= 0.2 and values.ndim == 1 and np.isfinite(values).all()
            assert np.max(np.abs(values)) > 1e-4
            samples.append({'language': language, 'text': text, 'audio_seconds': duration,
                            'processing_seconds': elapsed, 'realtime_multiplier': duration / elapsed,
                            'rms': float(np.sqrt(np.mean(values**2))),
                            'execution': fast_multilingual.execution_info()})
        if args.asr_reference is not None:
            # Check the actual isolated recognizer and its persistent cache,
            # using only the checked public English reference from audio.cpp.
            from native_transcript import reference_transcript
            started = time.monotonic()
            recognized = reference_transcript(args.asr_reference, args.data_dir, 'en-US')
            assert len(recognized.split()) >= 5, 'Public reference transcription is unexpectedly short'
            asr_elapsed = time.monotonic() - started
            cache = args.data_dir / 'cache/native-transcripts'
            cached_before = {p.name: (p.stat().st_mtime_ns, p.read_bytes()) for p in cache.glob('*.json')}
            assert reference_transcript(args.asr_reference, args.data_dir, 'en-US') == recognized
            assert cached_before == {p.name: (p.stat().st_mtime_ns, p.read_bytes()) for p in cache.glob('*.json')}
            output = audio_directory / 'native-public-missing-transcript.wav'
            synthesize = fast_multilingual.create_synthesizer(
                args.asr_reference.resolve(), args.data_dir.resolve(), threads=4,
                steps=8, device='cpu', language='fr', reference_text='', reference_language='en-US')
            synthesize('Bonjour, ceci est un test.', output)
            audio, rate = sf.read(output, dtype='float32')
            assert rate == 24000 and audio.ndim == 1 and len(audio) >= rate * .2
            assert np.isfinite(audio).all() and np.max(np.abs(audio)) > 1e-4
            asr_check = {'public_reference_only': True, 'reference_language': 'en-US',
                         'output_language': 'fr', 'local_cpu_transcription': True,
                         'processing_seconds': asr_elapsed, 'persistent_cache_reused': True,
                         'blank_transcript_synthesis_passed': True}
        result = {'platform': 'native-windows-x64', 'device': 'cpu',
                  'app_source_commit': os.environ.get('GITHUB_SHA'),
                  'native_source_run': os.environ.get('NATIVE_SOURCE_RUN_ID'),
                  'native_source_commit': os.environ.get('NATIVE_SOURCE_COMMIT'),
                  'public_reference_only': True, 'private_recordings_used': False,
                  'requests': samples, 'valid_pcm_audio': True,
                  'missing_reference_transcript': asr_check,
                  'gtx1060_tested': False, 'actual_hour_generated': False,
                  'target_30x_guaranteed': False, 'human_pronunciation_reviewed': False}
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False), flush=True)
    finally:
        fast_multilingual.close_backends()


if __name__ == '__main__':
    main()
