"""Independent real Windows CPU checks for native UTF-8 and 30-second references.

Only public inputs and JSON metadata are published. No Qwen/Nano/Turbo inference,
private voice unlock or GPU inference is performed by this probe.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import locale
import os
from pathlib import Path
import shutil
import stat
import sys
import time
import zipfile

from smoke_clean_bundle import configure, digest

SOURCE_SHA = 'a4646d2ab03d0ea9f605961dc7cde8fee4c512cc70344764564f3130fd3e2864'
REFERENCE_SHA = '32bf74dfb8342ccc8284f47a9e5fe1f41b458a983a00938ed170f76951ce638f'
PRIVATE_PACK_SHA = '1992c607a8ea9f64aa1821c751259698c146743a10b3da5b73f5738816fb7d82'
TEXT_POLICY = 'unicode-whitespace+ctype-C-v1'


def require(value, message):
    if not value:
        raise ValueError(message)


def notice(message, *, error=False):
    message = str(message).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print(('::error' if error else '::notice') + ' title=Native Windows regression::' + message, flush=True)


def stage(archive, root, source):
    """Retain just the verified public runtime, native CPU model and encrypted pack."""
    from build_full_update import _sources, application_digest
    from build_windows import safe_zip_path
    archive, root, source = Path(archive), Path(root), Path(source)
    require(digest(archive) == SOURCE_SHA, 'Full source archive SHA256 mismatch')
    require(not root.exists(), 'Use a fresh regression directory')
    current, version = _sources(source.resolve())
    root.mkdir(parents=True)
    retained = 0
    required = {'runtime/python.exe', 'runtime-native/cpu/audiocpp.dll',
                'app/.data/models/voxcpm-native.ready', 'delivery/manifest.json', 'delivery/voices.vspack'}
    copied, roots, folded = set(), set(), set()
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            parts = safe_zip_path(entry)
            require(bool(parts), 'Empty source ZIP path')
            roots.add(parts[0])
            if entry.is_dir():
                continue
            require(len(parts) >= 2 and stat.S_IFMT(entry.external_attr >> 16) in {0, stat.S_IFREG},
                    'Invalid source ZIP file')
            name = '/'.join(parts[1:])
            require(name.casefold() not in folded, 'Case-colliding source paths')
            folded.add(name.casefold())
            keep = (name in required or name.startswith(('runtime/', 'runtime-native/cpu/',
                                                       'app/.data/models/voxcpm2-native/')))
            if not keep or '__pycache__' in parts:
                continue
            require('voice-library' not in parts,
                    'Unexpected private/generated source path')
            target = root.joinpath(*parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(entry) as incoming, target.open('xb') as output:
                shutil.copyfileobj(incoming, output, 8 * 1024**2)
            copied.add(name)
            retained += 1
    require(len(roots) == 1 and required <= copied, 'The verified source lacks required native components')
    for name, payload in current.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    require(digest(root / 'delivery/voices.vspack') == PRIVATE_PACK_SHA, 'Encrypted private pack changed')
    report = {'format': 'native-regression-stage-v1', 'source_archive_sha256': SOURCE_SHA,
              'application_source_sha256': application_digest(current), 'application_version': version,
              'application_source_commit': os.environ.get('GITHUB_SHA'), 'retained_public_files': retained,
              'private_voice_unlock_attempted': False, 'encrypted_private_pack_preserved': True}
    (root / 'NATIVE-REGRESSION-STAGE.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def run(root, reference, output):
    root, reference, output = Path(root).resolve(), Path(reference).resolve(), Path(output).resolve()
    require(not output.exists(), 'Use a fresh report path')
    runtime, data = configure(root)
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    require(digest(reference) == REFERENCE_SHA, 'Only the pinned public reference may be used')
    require(digest(root / 'delivery/voices.vspack') == PRIVATE_PACK_SHA, 'Encrypted private pack changed')
    import numpy as np
    import soundfile as sf
    import fast_multilingual
    for module in (np, sf):
        require(runtime in Path(module.__file__).resolve().parents, 'Dependency escaped the bundled runtime')
    source = json.loads((root / 'NATIVE-REGRESSION-STAGE.json').read_text(encoding='utf-8'))
    report = {**source, 'format': 'voice-studio-native-windows-regression-v1', 'platform': sys.platform,
              'device': 'cpu', 'steps': 4, 'complete': False, 'requests': [],
              'public_reference_sha256': REFERENCE_SHA, 'private_recordings_used': False,
              'private_voice_unlock_attempted': False, 'gpu_inference_tested': False,
              'actual_hour_generated': False, 'target_30x_guaranteed': False,
              'human_pronunciation_reviewed': False}
    qa_audio = data / 'qa-audio/native-regression'
    qa_audio.mkdir(parents=True)
    original_locale = locale.setlocale(locale.LC_CTYPE)
    phase = 'character locale setup'
    try:
        caller_locale = locale.setlocale(locale.LC_CTYPE, '.1252')
        require(caller_locale.endswith('1252'), 'The main caller is not using Windows code page 1252')
        report['main_caller_lc_ctype'] = caller_locale
        public, rate = sf.read(reference, dtype='float32')
        require(public.ndim == 1 and 14 <= len(public) / rate <= 14.2, 'Unexpected pinned public WAV')
        long_reference = qa_audio / 'public-thirty-second-reference.wav'
        samples = np.tile(public, 3)[:30 * rate]
        require(len(samples) == 30 * rate, 'Could not construct the full thirty-second public reference')
        sf.write(long_reference, samples, rate, subtype='PCM_16')
        long_sha = digest(long_reference)
        cases = (
            ('Korean UTF-8', 'ko', '선택한 목소리의 속도를 측정하기 위해 짧은 글을 읽습니다.', reference),
            ('Chinese UTF-8', 'zh', '你好。', reference),
            ('Full thirty-second reference', 'zh', '你好。', long_reference),
        )
        for index, (phase, language, text, selected_reference) in enumerate(cases):
            notice('BEGIN ' + phase)
            synthesize = fast_multilingual.create_synthesizer(selected_reference, data, threads=4, steps=4,
                                                             device='cpu', language=language, family='voxcpm2')
            destination = qa_audio / f'public-{index}-{language}.wav'
            started = time.perf_counter()
            synthesize(text, destination)
            elapsed = time.perf_counter() - started
            audio, audio_rate = sf.read(destination, dtype='float32')
            require(audio_rate == 24000 and audio.ndim == 1 and len(audio) >= audio_rate * .2
                    and np.isfinite(audio).all() and np.max(np.abs(audio)) > .0001,
                    'Native synthesis returned invalid or silent 24 kHz mono PCM')
            execution = fast_multilingual.execution_info()
            require(execution.get('backend') == 'voxcpm_native' and execution.get('model_family') == 'voxcpm2'
                    and execution.get('device') == 'cpu' and execution.get('voxcpm_steps') == 4
                    and execution.get('native_text_handling') == TEXT_POLICY,
                    'The actual isolated child did not confirm CPU/four-step Unicode-safe native execution')
            require(locale.setlocale(locale.LC_CTYPE) == caller_locale, 'The native child changed the main caller locale')
            row = {'case': phase, 'language': language, 'text': text, 'valid_pcm': True,
                   'audio_seconds': len(audio) / audio_rate, 'processing_seconds': elapsed,
                   'includes_first_model_load': index == 0, 'audio_sha256': digest(destination), 'execution': execution}
            if selected_reference == long_reference:
                require(execution.get('voxcpm_reference_encoder_capacity') == 481280,
                        'The full-reference encoder capacity is not 481280')
                require(digest(long_reference) == long_sha and sf.info(long_reference).duration == 30,
                        'The thirty-second reference was changed or shortened')
                row.update(reference_seconds=30, reference_sha256=long_sha,
                           reference_audio_preserved=True, includes_session_resize=True)
            report['requests'].append(row)
            notice('END ' + phase + ' | valid PCM | ' + str(round(row['audio_seconds'], 3)) + ' seconds audio')
        require(digest(reference) == REFERENCE_SHA and digest(root / 'delivery/voices.vspack') == PRIVATE_PACK_SHA,
                'The public reference or encrypted private pack changed')
        require(not (root / 'app/voice-library').exists(), 'The probe must never unlock private voices')
        report.update(complete=True, native_text_handling=TEXT_POLICY,
                      thirty_second_reference_capacity=481280, public_reference_unchanged=True)
    except Exception as exc:
        message = str(exc).replace(str(root), '<portable>').replace(str(reference), '<public-reference>')
        report.update(failed_phase=phase, error_type=type(exc).__name__, error=message[:2000])
        log = data / 'international-native-backend.log'
        tail = ''
        if log.is_file():
            with log.open('rb') as stream:
                stream.seek(max(0, log.stat().st_size - 4096))
                tail = stream.read().decode('utf-8', 'replace').replace(str(root), '<portable>')
        notice('FAILED ' + phase + ': ' + message + ' | native stderr: ' + tail, error=True)
        raise
    finally:
        try:
            fast_multilingual.close_backends()
        finally:
            locale.setlocale(locale.LC_CTYPE, original_locale)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    prepare = modes.add_parser('stage')
    prepare.add_argument('--archive', required=True, type=Path)
    prepare.add_argument('--root', required=True, type=Path)
    prepare.add_argument('--source', required=True, type=Path)
    probe = modes.add_parser('run')
    probe.add_argument('--root', required=True, type=Path)
    probe.add_argument('--reference', required=True, type=Path)
    probe.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.mode == 'stage':
        print(json.dumps(stage(args.archive, args.root, args.source), indent=2), flush=True)
    else:
        run(args.root, args.reference, args.output)


if __name__ == '__main__':
    main()
