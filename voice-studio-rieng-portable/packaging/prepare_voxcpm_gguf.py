"""Convert the verified public VoxCPM2 checkpoint to a local native Q8 model.

No downloads or source-checkpoint edits. The converter must come from the
pinned native build; AudioVAE is read with weights_only=True and its safetensors
round trip must preserve every tensor before any lossy GGUF quantization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

APP = Path(__file__).resolve().parents[1] / 'app'
sys.path.insert(0, str(APP))
from native_voxcpm_model import (MARKER_NAME, MODEL_DIRECTORY, MODEL_FILENAME,
                                 MODEL_REPOSITORY, MODEL_REVISION, NATIVE_REVISION)
from public_modelpack import PROVENANCE_SHA256


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_source(source):
    source = Path(source)
    if source.is_symlink() or not source.is_dir():
        raise ValueError('The original model must be a real directory')
    source = source.resolve()
    provenance = source / 'MODEL_PROVENANCE.json'
    if provenance.is_symlink() or sha256(provenance) != PROVENANCE_SHA256:
        raise ValueError('Original VoxCPM2 provenance SHA256 differs from the verified public package')
    record = json.loads(provenance.read_text(encoding='utf-8'))
    if record.get('repository') != MODEL_REPOSITORY or record.get('revision') != MODEL_REVISION:
        raise ValueError('The original checkpoint repository or revision differs')
    files = record.get('files')
    if not isinstance(files, list) or not files:
        raise ValueError('The original model manifest is empty')
    validated = {}
    for item in files:
        name, size, expected = item.get('name'), item.get('size'), item.get('sha256')
        if (not isinstance(name, str) or Path(name).name != name or '\\' in name
                or name in {'', '.', '..'} or ':' in name or name in validated
                or type(size) is not int or size <= 0
                or not isinstance(expected, str) or len(expected) != 64
                or any(char not in '0123456789abcdef' for char in expected)):
            raise ValueError('The original model manifest contains an invalid record')
        path = source / name
        if (path.is_symlink() or not path.is_file() or path.stat().st_size != size
                or sha256(path) != expected):
            raise ValueError('Original model SHA256/size mismatch: ' + name)
        validated[name] = {'size': size, 'sha256': expected}
    required = {'model.safetensors', 'audiovae.pth', 'config.json',
                'tokenizer.json', 'tokenizer_config.json', 'special_tokens_map.json'}
    if not required <= validated.keys():
        raise ValueError('The original model is missing required verified files')
    config = json.loads((source / 'config.json').read_text(encoding='utf-8'))
    if config.get('architecture') != 'voxcpm2':
        raise ValueError('The source checkpoint is not VoxCPM2')
    return source, validated


def verify_converter(converter):
    converter = Path(converter)
    if converter.is_symlink() or not converter.is_file():
        raise ValueError('The pinned native GGUF converter is missing')
    converter = converter.resolve()
    manifest_path = converter.parent / 'native-build.json'
    if manifest_path.is_symlink():
        raise ValueError('The native converter manifest must not be a symlink')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if (manifest.get('revision') != NATIVE_REVISION
            or 'voxcpm2' not in manifest.get('families', [])
            or manifest.get('tools_sha256', {}).get(converter.name) != sha256(converter)):
        raise ValueError('The GGUF converter is not from the pinned VoxCPM2 native build')
    # An executable can depend on the staged libraries: verify those too.
    for name, expected in manifest.get('sha256', {}).items():
        if Path(name).name != name or sha256(converter.parent / name) != expected:
            raise ValueError('Native converter runtime SHA256 mismatch')
    return converter, manifest


def convert_vae(source, destination):
    import torch
    from safetensors.torch import load_file, save_file

    payload = torch.load(str(source), map_location='cpu', weights_only=True)
    if not isinstance(payload, dict):
        raise ValueError('AudioVAE checkpoint must contain a tensor dictionary')
    state = payload.get('state_dict', payload)
    if not isinstance(state, dict) or not state:
        raise ValueError('AudioVAE tensor dictionary is missing')
    tensors = {}
    for name, value in state.items():
        if not isinstance(name, str) or not torch.is_tensor(value):
            raise ValueError('AudioVAE contains a non-tensor value')
        tensors[name] = value.detach().cpu().contiguous()
    save_file(tensors, str(destination), metadata={'source_format': 'pytorch',
                                                  'source_sha256': sha256(source)})
    restored = load_file(str(destination), device='cpu')
    if set(restored) != set(tensors):
        raise ValueError('AudioVAE safetensors keys changed during conversion')
    for name, tensor in tensors.items():
        actual = restored[name]
        if actual.dtype != tensor.dtype or actual.shape != tensor.shape or not torch.equal(actual, tensor):
            raise ValueError('AudioVAE tensor changed during conversion: ' + name)
    return {'tensor_count': len(tensors), 'sha256': sha256(destination),
            'tensor_roundtrip_exact': True}


def _install(converted, destination, marker, record, sidecars=None):
    """Commit model and marker together; a failed marker write restores old data."""
    for path in (destination, destination.parent, marker, marker.parent):
        if path.is_symlink():
            raise ValueError('Prepared model destinations must not be symlinks')
    destination.parent.mkdir(parents=True, exist_ok=True)
    marker.parent.mkdir(parents=True, exist_ok=True)
    ident = uuid.uuid4().hex
    new_model = destination.with_name('.' + destination.name + '.' + ident + '.tmp')
    new_marker = marker.with_name('.' + marker.name + '.' + ident + '.tmp')
    replacements = {destination: new_model}
    sidecar_staging = []
    backups = {}
    replaced = []
    try:
        shutil.copy2(converted, new_model)
        if sha256(new_model) != record['sha256']:
            raise ValueError('Converted model copy SHA256 mismatch')
        for name, payload in (sidecars or {}).items():
            if Path(name).name != name or name in {MODEL_FILENAME, '.', '..'}:
                raise ValueError('Invalid prepared model sidecar name')
            target = destination.parent / name
            if target.is_symlink():
                raise ValueError('Prepared model sidecars must not be symlinks')
            temporary = target.with_name('.' + target.name + '.' + ident + '.tmp')
            sidecar_staging.append(temporary)
            temporary.write_bytes(payload)
            replacements[target] = temporary
        new_marker.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        try:
            for target, temporary in replacements.items():
                if target.exists():
                    previous = target.with_name('.' + target.name + '.' + ident + '.backup')
                    os.replace(target, previous)
                    backups[target] = previous
                os.replace(temporary, target)
                replaced.append(target)
            os.replace(new_marker, marker)
        except BaseException:
            for target in reversed(replaced):
                target.unlink(missing_ok=True)
            for target, previous in backups.items():
                os.replace(previous, target)
            raise
        for previous in backups.values():
            previous.unlink(missing_ok=True)
    finally:
        new_model.unlink(missing_ok=True)
        new_marker.unlink(missing_ok=True)
        for temporary in sidecar_staging:
            temporary.unlink(missing_ok=True)


def prepare(source_model, converter, data, work_dir=None):
    source, originals = verify_source(source_model)
    converter, build = verify_converter(converter)
    data = Path(data).resolve()
    models = data / 'models'
    marker = models / MARKER_NAME
    destination = models / MODEL_DIRECTORY / MODEL_FILENAME
    if marker.is_file():
        from native_voxcpm_model import prepared_model
        try:
            _, existing = prepared_model(data, verify=True)
            if (existing.get('original_files_sha256') == {name: row['sha256'] for name, row in originals.items()}
                    and existing.get('converter_sha256') == sha256(converter)):
                return {**existing, 'already_prepared': True}
        except (OSError, ValueError, KeyError, TypeError):
            pass
    scratch = Path(work_dir).resolve() if work_dir else models
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='voxcpm-native-convert-', dir=scratch) as temporary:
        temporary = Path(temporary)
        stage = temporary / 'source'
        stage.mkdir()
        # Only verified, public sidecars are embedded in the portable GGUF.
        # Original model, config and checkpoint files remain untouched.
        for name in originals:
            if name.endswith(('.json', '.model', '.txt', '.md')):
                shutil.copy2(source / name, stage / name)
        derived = stage / 'audiovae.safetensors'
        vae = convert_vae(source / 'audiovae.pth', derived)
        converted = temporary / MODEL_FILENAME
        command = [str(converter), '--input', 'weights=' + str(source / 'model.safetensors'),
                   '--input', 'audiovae_weights=' + str(derived), '--family', 'voxcpm2',
                   '--root', str(stage), '--type', 'q8_0', '--output', str(converted)]
        subprocess.run(command, check=True, timeout=3600)
        if not converted.is_file() or converted.stat().st_size < 4:
            raise ValueError('The native converter did not produce a GGUF model')
        with converted.open('rb') as stream:
            if stream.read(4) != b'GGUF':
                raise ValueError('The native converter output is not a GGUF model')
        subprocess.run([str(converter), '--inspect', str(converted)], check=True, timeout=180)
        # Recheck every source fingerprint after the external converter exits.
        verify_source(source)
        record = {
            'schema': 1, 'backend': 'voxcpm_native', 'repository': MODEL_REPOSITORY,
            'revision': MODEL_REVISION, 'native_source_revision': NATIVE_REVISION,
            'model_dir': MODEL_DIRECTORY, 'filename': MODEL_FILENAME,
            'quantization': 'q8_0', 'sha256': sha256(converted), 'size': converted.stat().st_size,
            'source_provenance_sha256': PROVENANCE_SHA256,
            'original_files_sha256': {name: row['sha256'] for name, row in originals.items()},
            'converter_sha256': sha256(converter), 'converter_device': build.get('device'),
            'audio_vae_safetensors': vae, 'original_weights_and_config_unchanged': True,
            'gpu_performance_tested': False, 'target_30x_guaranteed': False,
            'private_reference_audio_included': False,
        }
        sidecars = {name: (source / name).read_bytes() for name in
                    ('LICENSE-APACHE-2.0.txt', 'README.md', 'MODEL_PROVENANCE.json')
                    if name == 'MODEL_PROVENANCE.json' or name in originals}
        _install(converted, destination, marker, record, sidecars)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-model', required=True, type=Path)
    parser.add_argument('--converter', required=True, type=Path)
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--work-dir', type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source_model, args.converter, args.data_dir, args.work_dir),
                     ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
