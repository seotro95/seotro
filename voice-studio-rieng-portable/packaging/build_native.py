"""Build the pinned, minimal audio.cpp C ABI for portable OmniVoice.

CPU uses an AVX2 baseline without host-specific AVX512/VNNI flags. The optional
CUDA build deliberately requires CUDA 12 and includes sm_61 for GTX 1060.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

NATIVE_REVISION = '2597b300f5961999387c84c65f2e8e79c088a571'
NATIVE_REPOSITORY = 'https://github.com/0xShug0/audio.cpp.git'


def run(*arguments, **kwargs):
    subprocess.run([str(value) for value in arguments], check=True, **kwargs)


def cmake_arguments(source, build, device):
    flags = [
        'cmake', '-S', str(source), '-B', str(build), '-G', 'Ninja',
        '-DCMAKE_BUILD_TYPE=Release', '-DAUDIOCPP_BUILD_C_API=ON',
        '-DAUDIOCPP_DEPLOYMENT_BUILD=ON',
        '-DAUDIOCPP_MODEL_SET=custom', '-DAUDIOCPP_MODELS=omnivoice',
        '-DENGINE_ENABLE_NATIVE_CPU=OFF', '-DENGINE_ENABLE_LLAMAFILE=OFF',
        '-DENGINE_BUILD_EXAMPLES=OFF', '-DENGINE_BUILD_TESTS=OFF',
        '-DENGINE_BUILD_WARMBENCH=OFF', '-DAUDIOCPP_BUILD_NATIVE_MODEL_MANAGER=OFF',
        '-DENGINE_ENABLE_METAL=OFF', '-DENGINE_ENABLE_VULKAN=OFF',
        '-DENGINE_ENABLE_CUDA_GRAPHS=OFF',
        '-DGGML_AVX=ON', '-DGGML_AVX2=ON', '-DGGML_FMA=ON', '-DGGML_F16C=ON',
        '-DGGML_AVX512=OFF', '-DGGML_AVX512_VBMI=OFF', '-DGGML_AVX512_VNNI=OFF',
        '-DGGML_AVX512_BF16=OFF', '-DGGML_AVX_VNNI=OFF',
        '-DGGML_AMX_TILE=OFF', '-DGGML_AMX_INT8=OFF', '-DGGML_AMX_BF16=OFF',
        '-DENGINE_ENABLE_CUDA=' + ('ON' if device == 'cuda' else 'OFF'),
    ]
    if device == 'cuda':
        flags += ['-DCMAKE_CUDA_ARCHITECTURES=61;75;86',
                  '-DGGML_CUDA_FORCE_MMQ=ON', '-DCMAKE_CUDA_FLAGS=-allow-unsupported-compiler']
    return flags


def stage_runtime(build, destination, device):
    destination.mkdir(parents=True, exist_ok=True)
    name = 'audiocpp.dll' if os.name == 'nt' else 'libaudiocpp.so'
    candidates = list(build.rglob(name))
    if len(candidates) != 1:
        raise ValueError('Expected exactly one built ' + name)
    shutil.copy2(candidates[0], destination / name)
    if os.name == 'nt':
        redist = os.environ.get('VCToolsRedistDir')
        if not redist:
            raise ValueError('VCToolsRedistDir is needed to stage the Visual C++ runtime')
        root = Path(redist) / 'x64'
        for pattern in ('Microsoft.VC*.CRT/*.dll', 'Microsoft.VC*.OpenMP/vcomp140.dll'):
            matches = list(root.glob(pattern))
            if not matches:
                raise ValueError('Missing Visual C++ redistributable: ' + pattern)
            for library in matches:
                shutil.copy2(library, destination / library.name)
        if device == 'cuda':
            cuda = os.environ.get('CUDA_PATH')
            if not cuda:
                raise ValueError('CUDA_PATH is needed to stage CUDA runtime DLLs')
            for pattern in ('cudart64_12.dll', 'cublas64_12.dll', 'cublasLt64_12.dll'):
                library = Path(cuda) / 'bin' / pattern
                if not library.is_file():
                    raise ValueError('Missing CUDA 12 runtime: ' + str(library))
                shutil.copy2(library, destination / library.name)


def build_native(source, build, destination, device='cpu', jobs=2):
    source, build, destination = (Path(value).resolve() for value in (source, build, destination))
    actual = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != NATIVE_REVISION:
        raise ValueError('Native source revision differs from the pinned version')
    if device == 'cuda':
        version = subprocess.check_output(['nvcc', '--version'], text=True)
        if not re.search(r'release 12\.', version):
            raise ValueError('CUDA 12 is required: CUDA 13 removes GTX 1060 / sm_61 support')
    run(*cmake_arguments(source, build, device))
    run('cmake', '--build', build, '--config', 'Release', '--target', 'audiocpp', '--parallel', str(jobs))
    stage_runtime(build, destination, device)
    notices = destination / 'licenses'
    notices.mkdir(exist_ok=True)
    shutil.copy2(source / 'LICENSE', notices / 'audio.cpp-LICENSE.txt')
    shutil.copy2(source / 'docs/model_licenses.md', notices / 'MODEL-LICENSE-REFERENCE.md')
    for directory in ('ggml', 'sentencepiece', 'cJSON', 'utf8proc', 'libyaml'):
        folder = source / 'external' / directory
        candidates = [p for p in folder.glob('*') if p.is_file() and p.name.lower().startswith(('license', 'copying'))]
        for license_file in candidates:
            shutil.copy2(license_file, notices / (directory + '-' + license_file.name))
    checksums = {}
    for library in sorted(destination.iterdir()):
        if library.is_file() and library.suffix.lower() in {'.dll', '.so', '.dylib'}:
            with library.open('rb') as stream:
                checksums[library.name] = hashlib.file_digest(stream, 'sha256').hexdigest()
    manifest = {
        'schema': 1, 'repository': NATIVE_REPOSITORY, 'revision': NATIVE_REVISION,
        'source_revision': NATIVE_REVISION, 'native_revision': NATIVE_REVISION,
        'abi': '0.2', 'family': 'omnivoice', 'device': device,
        'cpu_baseline': 'AVX2/FMA/F16C; no AVX512/VNNI',
        'cuda_architectures': ['61', '75', '86'] if device == 'cuda' else [],
        'cuda_toolkit_major': 12 if device == 'cuda' else None,
        'sha256': checksums, 'gpu_performance_tested': False,
    }
    (destination / 'native-build.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    parser.add_argument('--jobs', type=int, default=2)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 64:
        parser.error('--jobs must be between 1 and 64')
    print(json.dumps(build_native(args.source, args.build, args.output, args.device, args.jobs), indent=2))


if __name__ == '__main__':
    main()
