"""Explicit, checksum-pinned preparation of the optional native OmniVoice model.

Normal speech generation never downloads anything. This installer needs only the
portable Python standard library; it does not change the Turbo Python runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import urllib.request
import uuid

BASE = Path(__file__).resolve().parent
NATIVE_REVISION = '2597b300f5961999387c84c65f2e8e79c088a571'
MODEL_REVISION = '874fcb41ececda20bcbc0782d6b4ea7f7d069ea8'
MODEL_SIZE = 1350296096
MODEL_SHA256 = '0e5a721edd1b08d9067ef66f40ded609a6b14f5a8445c703f9869736cabd350a'
MODEL_FILENAME = 'omnivoice-q8_0.gguf'
MODEL_URL = ('https://github.com/seotro95/seotro/releases/download/'
             'omnivoice-model-40894029886/' + MODEL_FILENAME)
SOURCE_URL = ('https://huggingface.co/audio-cpp/audio.cpp-gguf/resolve/' + MODEL_REVISION
              + '/OmniVoice-GGUF/' + MODEL_FILENAME)
ASR_REPOSITORY = 'Systran/faster-whisper-base'
ASR_REVISION = 'ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66'
ASR_VERSION = '1.2.1'
ASR_FILES = [
    {'name': 'config.json', 'size': 2309, 'sha256': '56a6d8110d311f19c8f0471e562832c7527f146b567275bfca59fcf7c184da9a'},
    {'name': 'model.bin', 'size': 145217532, 'sha256': 'd01c3014881c9c6f3133c182f3d2887eb6ca1c789a7538c5c007196857a0a6a9'},
    {'name': 'tokenizer.json', 'size': 2203239, 'sha256': 'fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab'},
    {'name': 'vocabulary.txt', 'size': 459861, 'sha256': '34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913'},
]
NOTICES = '''OmniVoice native Q8 model provenance
Original model: https://huggingface.co/k2-fsa/OmniVoice
Original code: https://github.com/k2-fsa/OmniVoice (Apache-2.0)
Model weights: CC-BY-NC; see the current model card, not the code license.
Embedded audio tokenizer: bosonai/higgs-audio-v2-tokenizer,
Boson Higgs Audio 2 Community License:
https://huggingface.co/bosonai/higgs-audio-v2-tokenizer
Native conversion: https://huggingface.co/audio-cpp/audio.cpp-gguf
Runtime: https://github.com/0xShug0/audio.cpp
Code and model licenses are distinct. This optional model is experimental;
it does not establish a synthesis speed or identical voice timbre.
No private recordings, passwords, scripts or user history are downloaded.
Optional offline transcription: OpenAI Whisper base / Systran CTranslate2
conversion (MIT), https://huggingface.co/Systran/faster-whisper-base .
Reference audio is transcribed locally only; no recording is uploaded.
'''


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def verify_model(path, expected_size=MODEL_SIZE, expected_sha256=MODEL_SHA256):
    path = Path(path)
    if path.stat().st_size != expected_size or digest(path) != expected_sha256:
        raise ValueError('Tệp mô hình OmniVoice không khớp SHA256; chưa kích hoạt mô hình.')
    with path.open('rb') as source:
        if source.read(4) != b'GGUF':
            raise ValueError('Tệp mô hình OmniVoice không có định dạng GGUF.')


def prepare(data, source=None, *, opener=urllib.request.urlopen):
    data = Path(data).resolve()
    model_dir = data / 'models' / 'omnivoice'
    model_dir.mkdir(parents=True, exist_ok=True)
    destination = model_dir / MODEL_FILENAME
    # Download to a unique sibling: failure leaves the previous verified model
    # and its readiness marker untouched.
    temporary = destination.with_name(destination.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        try:
            verify_model(destination)
            valid_existing = True
        except (OSError, ValueError):
            valid_existing = False
        if not valid_existing:
            if source is not None:
                with Path(source).open('rb') as incoming, temporary.open('xb') as output:
                    shutil.copyfileobj(incoming, output, 8 * 1024**2)
            else:
                request = urllib.request.Request(MODEL_URL, headers={'User-Agent': 'Voice-Studio-Native-Preparation/1.11'})
                print('Đang tải mô hình OmniVoice 1,35 GB; giữ cửa sổ này mở.', flush=True)
                received = 0
                next_notice = 128 * 1024**2
                with opener(request, timeout=120) as incoming, temporary.open('xb') as output:
                    while block := incoming.read(8 * 1024**2):
                        received += len(block)
                        if received > MODEL_SIZE:
                            raise ValueError('Tệp tải vượt kích thước đã xác minh.')
                        output.write(block)
                        if received >= next_notice:
                            print(f'Đã tải {received * 100 // MODEL_SIZE}%.', flush=True)
                            next_notice += 128 * 1024**2
            verify_model(temporary)
            temporary.replace(destination)
        marker = {
            'schema': 1, 'backend': 'omnivoice', 'model_dir': 'omnivoice',
            'filename': MODEL_FILENAME, 'model': 'omnivoice/' + MODEL_FILENAME,
            'repository': 'audio-cpp/audio.cpp-gguf', 'revision': MODEL_REVISION,
            'source_revision': MODEL_REVISION, 'native_revision': NATIVE_REVISION,
            'size': MODEL_SIZE, 'sha256': MODEL_SHA256, 'source_url': SOURCE_URL,
            'license': 'CC-BY-NC', 'tokenizer_license': 'Boson Higgs Audio 2 Community License',
            'private_reference_audio_included': False, 'speech_speed_claimed': False,
        }
        (model_dir / 'SOURCE-AND-LICENSE.txt').write_text(NOTICES + '\nFrozen source: ' + SOURCE_URL + '\n', encoding='utf-8')
        (model_dir / 'MODEL_PROVENANCE.json').write_text(json.dumps(marker, indent=2) + '\n', encoding='utf-8')
        marker_path = data / 'models' / 'omnivoice.ready'
        marker_temporary = marker_path.with_name(marker_path.name + '.' + uuid.uuid4().hex + '.tmp')
        try:
            marker_temporary.write_text(json.dumps(marker, indent=2) + '\n', encoding='utf-8')
            marker_temporary.replace(marker_path)
        finally:
            marker_temporary.unlink(missing_ok=True)
        return marker
    finally:
        temporary.unlink(missing_ok=True)


def _verify_asr_file(path, record):
    return Path(path).stat().st_size == record['size'] and digest(path) == record['sha256']


def prepare_asr(data, source=None, *, opener=urllib.request.urlopen):
    """Prepare the small local recognizer required when a voice has no text.

    A complete directory is staged before swapping it into place, so interrupted
    setup never exposes a partially downloaded recognizer as ready.
    """
    models = Path(data).resolve() / 'models'
    models.mkdir(parents=True, exist_ok=True)
    destination = models / 'native-asr'
    temporary = models / ('native-asr.' + uuid.uuid4().hex + '.tmp')
    backup = models / ('native-asr.' + uuid.uuid4().hex + '.previous')
    manifest = {'schema': 1, 'repository': ASR_REPOSITORY, 'revision': ASR_REVISION,
                'package': 'faster-whisper', 'version': ASR_VERSION,
                'files': ASR_FILES, 'license': 'MIT', 'offline_reference_transcription': True,
                'reference_audio_uploaded': False}
    try:
        valid_existing = all(_verify_asr_file(destination / record['name'], record) for record in ASR_FILES)
    except OSError:
        valid_existing = False
    if valid_existing:
        marker = destination / 'VOICE-STUDIO-ASR.json'
        marker_temporary = marker.with_name(marker.name + '.' + uuid.uuid4().hex + '.tmp')
        try:
            marker_temporary.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
            marker_temporary.replace(marker)
        finally:
            marker_temporary.unlink(missing_ok=True)
        return manifest
    temporary.mkdir()
    try:
        print('Chuẩn bị bộ nhận lời mẫu giọng ngoại tuyến (148 MB). Không tải lên tệp giọng của bạn.', flush=True)
        for record in ASR_FILES:
            name = record['name']
            target = temporary / name
            if source is not None:
                shutil.copy2(Path(source) / name, target)
            else:
                existing = destination / name
                try:
                    reusable = _verify_asr_file(existing, record)
                except OSError:
                    reusable = False
                if reusable:
                    shutil.copy2(existing, target)
                else:
                    url = 'https://huggingface.co/' + ASR_REPOSITORY + '/resolve/' + ASR_REVISION + '/' + name
                    request = urllib.request.Request(url, headers={'User-Agent': 'Voice-Studio-Native-Preparation/1.11'})
                    count = 0
                    with opener(request, timeout=120) as incoming, target.open('xb') as output:
                        while block := incoming.read(8 * 1024**2):
                            count += len(block)
                            if count > record['size']:
                                raise ValueError('ASR download exceeds the pinned file size')
                            output.write(block)
            if not _verify_asr_file(target, record):
                raise ValueError('SHA256 của bộ nhận lời mẫu giọng không khớp: ' + name)
        (temporary / 'VOICE-STUDIO-ASR.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        (temporary / 'SOURCE-AND-LICENSE.txt').write_text(
            'Whisper base multilingual model: MIT\nhttps://github.com/openai/whisper\n'
            'CTranslate2 conversion: https://huggingface.co/' + ASR_REPOSITORY + '/tree/' + ASR_REVISION
            + '\nReference recordings are processed locally and never uploaded.\n', encoding='utf-8')
        if destination.exists():
            destination.rename(backup)
        try:
            temporary.rename(destination)
        except BaseException:
            if backup.exists():
                backup.rename(destination)
            raise
        shutil.rmtree(backup, ignore_errors=True)
        return manifest
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path(os.environ.get('VOICE_STUDIO_DATA_DIR', str(BASE / '.data'))))
    parser.add_argument('--model-source', type=Path, help='Use an already downloaded model after the same SHA256 checks')
    parser.add_argument('--asr-source', type=Path, help='Use a local Whisper model directory after the same SHA256 checks')
    parser.add_argument('--model-only', action='store_true', help='Prepare weights before the native library is staged (CI)')
    args = parser.parse_args()
    if not args.model_only:
        library = BASE.parent / 'runtime-native' / 'cpu' / ('audiocpp.dll' if os.name == 'nt' else 'libaudiocpp.so')
        if not library.is_file():
            raise SystemExit('Thiếu bộ chạy native. Giải nén bản Windows 1.11 đầy đủ rồi chạy lại tệp tải giọng nhanh.')
        if not (BASE.parent / 'runtime-native/asr/faster_whisper').is_dir():
            raise SystemExit('Thiếu bộ nhận lời mẫu giọng ngoại tuyến. Dùng gói Windows 1.11 có runtime-native\\asr.')
    print(NOTICES, flush=True)
    prepare_asr(args.data_dir, args.asr_source)
    prepare(args.data_dir, args.model_source)
    print('Đã kiểm tra SHA256 và chuẩn bị OmniVoice. Mở lại tool, chọn bộ đọc OmniVoice và đo/nghe mẫu.', flush=True)


if __name__ == '__main__':
    main()
