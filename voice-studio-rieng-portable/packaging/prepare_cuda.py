"""Stage official, checksum-pinned CUDA 12.6 Windows components without an installer.

The Windows network installer rejects Linux-only component names and can try to
install a display driver on a CPU-only runner. NVIDIA's redistributable archives
provide the compiler, libraries and headers needed for a Ninja build directly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import urllib.request
import uuid
import zipfile

BASE_URL = 'https://developer.download.nvidia.com/compute/cuda/redist/'
SOURCE_MANIFEST = BASE_URL + 'redistrib_12.6.3.json'
# Frozen from NVIDIA's official 12.6.3 redistributable manifest, windows-x86_64.
COMPONENTS = [
    {'name': 'cuda_nvcc', 'path': 'cuda_nvcc/windows-x86_64/cuda_nvcc-windows-x86_64-12.6.85-archive.zip',
     'size': 79950764, 'sha256': '3fb9f76b87c37d02f947354be89b718ad5f2c76b6ab47995265bfa3a068a5e14'},
    {'name': 'cuda_cudart', 'path': 'cuda_cudart/windows-x86_64/cuda_cudart-windows-x86_64-12.6.77-archive.zip',
     'size': 2512007, 'sha256': '7a313bc0c93b1a50bb03aa9783a199ae70c3b66e2d8084da65e8254a8577b925'},
    {'name': 'cuda_cccl', 'path': 'cuda_cccl/windows-x86_64/cuda_cccl-windows-x86_64-12.6.77-archive.zip',
     'size': 2929962, 'sha256': '469b783b6731964170b3d27ae214e97e2a63ec93c57ace3ed4052e6d01261f2e'},
    {'name': 'libcublas', 'path': 'libcublas/windows-x86_64/libcublas-windows-x86_64-12.6.4.1-archive.zip',
     'size': 428583217, 'sha256': '1a87ec80f8c0e5a39badc87010d479930c5b63abd788b3a05bd688a5980a3d07'},
    {'name': 'libcufft', 'path': 'libcufft/windows-x86_64/libcufft-windows-x86_64-11.3.0.4-archive.zip',
     'size': 197843242, 'sha256': '7b3c75e90a907b3a2d215f7c846d67b684c6ddb76369d1bced67d2cdd411014b'},
    {'name': 'cuda_nvml_dev', 'path': 'cuda_nvml_dev/windows-x86_64/cuda_nvml_dev-windows-x86_64-12.6.77-archive.zip',
     'size': 129922, 'sha256': '45f2466ff154a44701388a90913b7d1c4c0ec591f0ec33b3d30464d5c2ffbe8d'},
]
REQUIRED = (
    'bin/nvcc.exe', 'bin/ptxas.exe', 'bin/cudart64_12.dll',
    'bin/cublas64_12.dll', 'bin/cublasLt64_12.dll', 'bin/cufft64_11.dll',
    'include/cuda_runtime.h', 'include/cublas_v2.h', 'include/cufft.h', 'include/thrust/version.h',
    'lib/x64/cudart.lib', 'lib/x64/cudart_static.lib', 'lib/x64/cublas.lib',
    'lib/x64/cufft.lib', 'nvvm/libdevice/libdevice.10.bc',
)


def sha256(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def verified(path, record):
    try:
        return path.stat().st_size == record['size'] and sha256(path) == record['sha256']
    except FileNotFoundError:
        return False


def download(record, directory, opener=urllib.request.urlopen):
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / PurePosixPath(record['path']).name
    if verified(destination, record):
        return destination
    temporary = destination.with_name(destination.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        request = urllib.request.Request(BASE_URL + record['path'], headers={'User-Agent': 'Voice-Studio-CUDA-Build/1.11'})
        count = 0
        with opener(request, timeout=120) as incoming, temporary.open('xb') as output:
            while block := incoming.read(8 * 1024**2):
                count += len(block)
                if count > record['size']:
                    raise ValueError('CUDA component exceeds the pinned archive size: ' + record['name'])
                output.write(block)
        if not verified(temporary, record):
            raise ValueError('CUDA archive SHA256 does not match: ' + record['name'])
        temporary.replace(destination)
        return destination
    finally:
        temporary.unlink(missing_ok=True)


def merge_component(archive, record, destination):
    expected_root = PurePosixPath(record['path']).name.removesuffix('.zip')
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            path = PurePosixPath(entry.filename)
            if (path.is_absolute() or '..' in path.parts or '\\' in entry.filename
                    or ':' in entry.filename or not path.parts or path.parts[0] != expected_root
                    or (entry.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError('Unsafe CUDA archive path')
            relative = path.parts[1:]
            if not relative or entry.is_dir():
                continue
            # Per-component EULAs and version metadata have overlapping names.
            # Retain them separately; compiler/runtime folders form one toolkit.
            if relative[0] not in {'bin', 'include', 'lib', 'nvvm', 'extras'}:
                relative = ('component-metadata', record['name'], *relative)
            target = destination.joinpath(*relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                with bundle.open(entry) as source:
                    expected = hashlib.file_digest(source, 'sha256').hexdigest()
                if sha256(target) != expected:
                    raise ValueError('Conflicting CUDA component file: ' + '/'.join(relative))
            else:
                with bundle.open(entry) as source, target.open('xb') as output:
                    shutil.copyfileobj(source, output, 1024**2)


def prepare(output, downloads, components=COMPONENTS, required=REQUIRED):
    output, downloads = Path(output).resolve(), Path(downloads).resolve()
    if output.exists():
        raise ValueError('Use a new CUDA toolkit output directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + '.' + uuid.uuid4().hex + '.tmp')
    temporary.mkdir()
    try:
        for record in components:
            print('Preparing official CUDA component ' + record['name'], flush=True)
            archive = download(record, downloads)
            merge_component(archive, record, temporary)
        missing = [name for name in required if not (temporary / name).is_file()]
        if missing:
            raise ValueError('CUDA toolkit is incomplete: ' + ', '.join(missing))
        metadata = {'schema': 1, 'cuda': '12.6.3', 'platform': 'windows-x86_64',
                    'source_manifest': SOURCE_MANIFEST, 'components': components,
                    'driver_installation_performed': False}
        (temporary / 'CUDA-REDISTRIBUTABLES.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
        temporary.rename(output)
        return metadata
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--downloads', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.output, args.downloads)
    print('Verified CUDA 12.6 toolkit: ' + str(args.output.resolve()), flush=True)


if __name__ == '__main__':
    main()
