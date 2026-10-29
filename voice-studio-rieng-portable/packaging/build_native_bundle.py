"""Overlay current source onto a checksum-verified public 1.10 installation.

The full archive includes native libraries and the encrypted voice installer.
OmniVoice weights are prepared explicitly afterward so every GitHub asset stays
below 2 GB. The smaller update contains no .data files or personal voice data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import zipfile

from build_windows import copy_source, safe_zip_path, sha256

BASE_SHA256 = '65446c1a1799699b3aadad616461e97cf66c049597c7ae9a5cbf3887f20312f6'
ROOT_NAME = 'Voice-Studio-Rieng-1.11.0-Native-Windows-x64'
GUIDE = '''VOICE STUDIO 1.11 - BO DOC DA NGON NGU NATIVE THU NGHIEM

Ban day du: giai nen vao thu muc moi, chay CAI_19_GIONG.bat bang mat khau cu
neu can cai cac mau giong, roi chay MO_TOOL.bat.
Giu lich su/giong rieng: chep app\\.data, app\\voice-library va
runtime-international tu ban cu.
Khong ghi de len thu muc cu khi tool dang mo.

De thu bo doc moi, chay TAI_GIONG_DA_NGON_NGU_NHANH.bat mot lan de tai
model da kiem tra SHA256 (1,35 GB) va bo nhan loi Whisper (148 MB).
Bo nhan loi xu ly mau giong tren may, khong gui tep len mang.
Trong tool chon bo doc OmniVoice,
giu dung giong/ngon ngu, do va nghe mau truoc khi tao ban dai.
Chon CUDA neu bo chay GPU da kem va driver NVIDIA ho tro CUDA 12.
GPU khong khoi dong duoc se bao loi, khong am tham doi sang CPU.

Mau giong duoc giu nguyen; mo hinh khac co the thay doi am sac/chat luong.
Toc do GTX 1060 va muc 1 gio/2 phut chua duoc chung minh.
VoxCPM va Turbo cu van co the dung khi cac mo hinh cu da cai.
OmniVoice weights: CC-BY-NC. Audio tokenizer: Boson Higgs Audio 2 Community
License. Xem app\\prepare_native.py va thong bao nguon sau khi tai model.

Ban cap nhat: dong tool, sao luu thu muc ban 1.10 va giai nen noi dung
Voice-Studio-1.11-Native-Update vao thu muc ban sao. Ban cap nhat khong
chua app\\.data, nen khong thay lich su, mau giong hay mo hinh da cai.
'''


def verify_native(directory):
    manifest = json.loads((directory / 'native-build.json').read_text(encoding='utf-8'))
    if manifest.get('revision') != '2597b300f5961999387c84c65f2e8e79c088a571':
        raise ValueError('Native runtime provenance differs from the pinned source')
    for name, expected in manifest['sha256'].items():
        if Path(name).name != name or sha256(directory / name) != expected:
            raise ValueError('Native runtime checksum mismatch')


def stage(base_archive, native_root, output):
    base_archive, native_root, output = map(Path, (base_archive, native_root, output))
    if sha256(base_archive) != BASE_SHA256:
        raise ValueError('The public 1.10 base archive SHA256 does not match')
    if output.exists():
        raise ValueError('Use a new output directory')
    output.mkdir(parents=True)
    with zipfile.ZipFile(base_archive) as archive:
        roots = {safe_zip_path(entry)[0] for entry in archive.infolist()}
        if len(roots) != 1:
            raise ValueError('Expected one portable root in the base archive')
        for entry in archive.infolist():
            parts = safe_zip_path(entry)[1:]
            if not parts:
                continue
            if any(part in {'.git', '.agents', '.codex', '.aws'} for part in parts):
                raise ValueError('Development metadata is not allowed in the portable archive')
            destination = output.joinpath(*parts)
            if entry.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as incoming, destination.open('xb') as target:
                    shutil.copyfileobj(incoming, target)
    if not (output / 'runtime/python.exe').is_file():
        raise ValueError('The base must contain Windows Python')
    # Replace code only. The verified base contains public models and encrypted
    # voice delivery; none of the caller's installation data is read.
    shutil.rmtree(output / 'app/static')
    copy_source(output)
    shutil.copy2(Path(__file__).resolve().parents[1] / 'requirements-native-asr.txt',
                 output / 'requirements-native-asr.txt')
    for device in ('cpu', 'cuda'):
        source = native_root / device
        if source.is_dir():
            verify_native(source)
            shutil.copytree(source, output / 'runtime-native' / device)
    asr = native_root / 'asr'
    if not (asr / 'faster_whisper').is_dir():
        raise ValueError('An isolated offline reference-transcription runtime is required')
    shutil.copytree(asr, output / 'runtime-native/asr')
    if not (output / 'runtime-native/cpu/audiocpp.dll').is_file():
        raise ValueError('A verified native CPU library is required')
    (output / 'DOC_TRUOC_NATIVE.txt').write_text(GUIDE, encoding='utf-8')
    build = {'version': '1.11.0', 'source_commit': os.environ.get('GITHUB_SHA'),
             'verified_base_sha256': BASE_SHA256, 'native_backend': 'omnivoice',
             'native_source_revision': '2597b300f5961999387c84c65f2e8e79c088a571',
             'native_model_bundled': False, 'native_model_explicit_download': True,
             'cuda_library_bundled': (output / 'runtime-native/cuda/audiocpp.dll').is_file(),
             'gtx1060_performance_tested': False, 'target_30x_guaranteed': False}
    old = output / 'BUILD_INFO.json'
    if old.exists():
        old.rename(output / 'BASE-1.10-BUILD_INFO.json')
    old.write_text(json.dumps(build, indent=2) + '\n', encoding='utf-8')
    (output / 'MANIFEST.sha256').unlink(missing_ok=True)


def package(root, output_directory):
    root, output_directory = map(Path, (root, output_directory))
    output_directory.mkdir(parents=True, exist_ok=True)
    archive = output_directory / (ROOT_NAME + '.zip')
    update = output_directory / 'Voice-Studio-1.11-Native-Update.zip'
    for destination, update_only in ((archive, False), (update, True)):
        with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=5) as bundle:
            for path in sorted(root.rglob('*')):
                if not path.is_file():
                    continue
                relative = path.relative_to(root)
                if '__pycache__' in relative.parts:
                    continue
                if update_only and not (
                        (relative.parts[0] == 'app' and '.data' not in relative.parts
                         and 'voice-library' not in relative.parts)
                        or relative.parts[0] == 'runtime-native'
                        or relative.as_posix() in {'TAI_GIONG_DA_NGON_NGU_NHANH.bat', 'DOC_TRUOC_NATIVE.txt',
                                                   'requirements-native-asr.txt', 'DOC_TRUOC.md'}):
                    continue
                name = (Path('Voice-Studio-1.11-Native-Update') if update_only else Path(ROOT_NAME)) / relative
                bundle.write(path, name.as_posix())
        if destination.stat().st_size >= 2 * 1024**3:
            raise ValueError('GitHub single release asset must stay below 2 GB')
        Path(str(destination) + '.sha256').write_text(sha256(destination) + '  ' + destination.name + '\n', encoding='utf-8')
    return archive, update


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_subparsers(dest='mode', required=True)
    stage_parser = mode.add_parser('stage')
    stage_parser.add_argument('--base-archive', required=True, type=Path)
    stage_parser.add_argument('--native-root', required=True, type=Path)
    stage_parser.add_argument('--root', required=True, type=Path)
    package_parser = mode.add_parser('package')
    package_parser.add_argument('--root', required=True, type=Path)
    package_parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.mode == 'stage':
        stage(args.base_archive, args.native_root, args.root)
    else:
        for path in package(args.root, args.output):
            print(path, flush=True)


if __name__ == '__main__':
    main()
