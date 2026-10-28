"""Package only the official public Apache-2.0 VoxCPM2 model, without loading it.

The download path requires huggingface-hub. Reassembly and archive self-tests use
only Python's standard library. Original config, weights and upstream checksums
are never changed. No application data, voice recordings or credentials enter
this pack.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
import zipfile

REPOSITORY = 'openbmb/VoxCPM2'
ENDPOINT = 'https://huggingface.co'
CHUNK_BYTES = 1400 * 1024**2  # 1,400 MiB, below both 1.4 GiB and GitHub's limit
APACHE_URL = 'https://www.apache.org/licenses/LICENSE-2.0.txt'
FOLDER = 'voxcpm2-original'


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+'\n', encoding='utf-8')


def safe_name(name):
    path = PurePosixPath(name)
    if not name or path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name or '\0' in name:
        raise ValueError('Unsafe model/manifest path: '+repr(name))
    return path


class ChunkWriter:
    """A non-seekable ZIP sink with bounded asset sizes and rolling checksums."""
    def __init__(self, directory, archive_name, maximum=CHUNK_BYTES):
        if not 1 <= maximum <= CHUNK_BYTES:
            raise ValueError('Chunk bytes must be positive and at most 1,400 MiB')
        self.directory, self.archive_name, self.maximum = Path(directory), archive_name, maximum
        self.position, self.parts, self.current = 0, [], None
        self.digest = hashlib.sha256()

    def tell(self):
        return self.position

    def flush(self):
        if self.current is not None:
            self.current.flush()

    def _close_part(self):
        self.current.close()
        self.parts.append({'name': self.current_path.name, 'size': self.part_size, 'sha256': self.part_digest.hexdigest()})
        self.current = None

    def write(self, data):
        view = memoryview(data)
        size = len(view)
        while view:
            if self.current is None:
                self.current_path = self.directory/(self.archive_name+f'.part{len(self.parts)+1:03d}')
                self.current = self.current_path.open('xb')
                self.part_size, self.part_digest = 0, hashlib.sha256()
            count = min(len(view), self.maximum-self.part_size)
            piece = view[:count]
            if self.current.write(piece) != count:
                raise OSError('Incomplete modelpack chunk write')
            self.part_digest.update(piece)
            self.digest.update(piece)
            self.part_size += count
            self.position += count
            view = view[count:]
            if self.part_size == self.maximum:
                self._close_part()
        return size

    def finish(self):
        if self.current is not None:
            self._close_part()
        return {'name': self.archive_name, 'size': self.position, 'sha256': self.digest.hexdigest(),
                'chunk_size_limit': self.maximum, 'chunks': self.parts}

    def close(self):
        if self.current is not None:
            self.current.close()
            self.current = None


class ChunkReader(io.RawIOBase):
    """Seek across split assets so ZIP CRC checks need no second full archive."""
    def __init__(self, directory, parts):
        super().__init__()
        self.handles, self.ends, total = [], [], 0
        for part in parts:
            self.handles.append((Path(directory)/part['name']).open('rb'))
            total += part['size']
            self.ends.append(total)
        self.total, self.position = total, 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        position = offset if whence == 0 else self.position+offset if whence == 1 else self.total+offset if whence == 2 else -1
        if position < 0:
            raise ValueError('Invalid seek')
        self.position = position
        return position

    def read(self, size=-1):
        remaining = max(0, self.total-self.position) if size < 0 else max(0, min(size, self.total-self.position))
        output = bytearray()
        while remaining:
            index = bisect.bisect_right(self.ends, self.position)
            begin = self.ends[index-1] if index else 0
            handle = self.handles[index]
            handle.seek(self.position-begin)
            block = handle.read(min(remaining, self.ends[index]-self.position))
            if not block:
                raise OSError('Truncated modelpack chunk')
            output.extend(block)
            remaining -= len(block)
            self.position += len(block)
        return bytes(output)

    def close(self):
        for handle in self.handles:
            handle.close()
        super().close()


def package_directory(source, assets, archive_name, maximum=CHUNK_BYTES):
    source, assets = Path(source), Path(assets)
    assets.mkdir(parents=True, exist_ok=True)
    sink = ChunkWriter(assets, archive_name, maximum)
    try:
        with zipfile.ZipFile(sink, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for file in sorted(source.rglob('*')):
                if file.is_symlink():
                    raise ValueError('Modelpack must contain materialized files, not symlinks')
                if not file.is_file():
                    continue
                name = FOLDER+'/'+file.relative_to(source).as_posix()
                safe_name(name)
                entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_STORED
                entry.external_attr = 0o100644 << 16
                entry.file_size = file.stat().st_size
                with file.open('rb') as input_file, archive.open(entry, 'w', force_zip64=True) as output:
                    shutil.copyfileobj(input_file, output, 1024*1024)
        result = sink.finish()
    finally:
        sink.close()
    with ChunkReader(assets, result['chunks']) as combined, zipfile.ZipFile(combined) as archive:
        broken = archive.testzip()
        if broken is not None:
            raise ValueError('Modelpack ZIP CRC mismatch: '+broken)
    return result


def reassemble(manifest_path, output):
    manifest_path, output = Path(manifest_path).resolve(), Path(output).resolve()
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    archive = manifest['archive']
    if output.exists():
        raise ValueError('Refusing to overwrite '+str(output))
    if not archive['chunks'] or sum(part['size'] for part in archive['chunks']) != archive['size']:
        raise ValueError('Invalid chunk sizes in manifest')
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=output.name+'.partial-', dir=output.parent)
    temporary = Path(temporary_name)
    overall, count = hashlib.sha256(), 0
    try:
        with os.fdopen(descriptor, 'wb') as target:
            for part in archive['chunks']:
                name = safe_name(part['name'])
                if len(name.parts) != 1:
                    raise ValueError('Chunk names must be plain filenames')
                path = manifest_path.parent/str(name)
                if path.is_symlink() or path.stat().st_size != part['size']:
                    raise ValueError('Chunk size/path mismatch: '+part['name'])
                actual = hashlib.sha256()
                with path.open('rb') as source:
                    for block in iter(lambda: source.read(1024*1024), b''):
                        actual.update(block)
                        overall.update(block)
                        count += len(block)
                        target.write(block)
                if actual.hexdigest() != part['sha256']:
                    raise ValueError('Chunk SHA256 mismatch: '+part['name'])
        if count != archive['size'] or overall.hexdigest() != archive['sha256']:
            raise ValueError('Reassembled archive SHA256 mismatch')
        if output.exists():
            raise ValueError('Output appeared during reassembly; refusing overwrite')
        temporary.rename(output)
    finally:
        temporary.unlink(missing_ok=True)
    print('VERIFIED REASSEMBLED ARCHIVE: '+str(output), flush=True)


def declared_apache(info, readme):
    card = getattr(info, 'card_data', None)
    if hasattr(card, 'to_dict'):
        card = card.to_dict()
    declared = card.get('license') if isinstance(card, dict) else None
    values = declared if isinstance(declared, list) else [declared] if declared else []
    if values:
        if len(values) != 1 or str(values[0]).strip().lower() != 'apache-2.0':
            raise ValueError('Official model metadata does not declare Apache-2.0: '+repr(declared))
        return {'method': 'official Hugging Face model-card metadata', 'declared': declared}
    frontmatter = readme.split('---', 2)[1] if readme.startswith('---') and readme.count('---') >= 2 else ''
    if re.search(r'(?mi)^license:\s*[\"\']?apache-2\.0[\"\']?\s*$', frontmatter):
        return {'method': 'official README YAML license declaration', 'declared': 'apache-2.0'}
    # Body fallback is deliberately explicit: a generic Apache link for software
    # dependencies is insufficient evidence for redistribution of model weights.
    if re.search(r'(?is)(?:this model|model weights|VoxCPM2)\s+(?:is|are)\s+(?:released|licensed|distributed)\s+under\s+(?:the\s+)?Apache(?:\s+License)?[\s,]*(?:Version\s*)?2\.0', readme):
        return {'method': 'explicit official README model-license statement', 'declared': 'apache-2.0'}
    raise ValueError('Apache-2.0 redistribution permission is not established; refusing to publish')


def selected_files(siblings):
    names = {str(item.rfilename) for item in siblings}
    for name in names:
        safe_name(name)
    weights = [next((name for name in choices if name in names), None)
               for choices in [('model.safetensors', 'pytorch_model.bin'), ('audiovae.safetensors', 'audiovae.pth')]]
    if not all(weights) or 'config.json' not in names or 'README.md' not in names:
        raise ValueError('Official snapshot lacks the required VoxCPM2 root config, model, AudioVAE or README')
    selected = set(weights)
    for name in names:
        path = PurePosixPath(name)
        if len(path.parts) != 1:
            continue
        if path.suffix.lower() in {'.json', '.model'} or name in {'merges.txt', 'vocab.txt'} or name.upper().startswith(('LICENSE', 'NOTICE')) or name == 'README.md':
            selected.add(name)
    if not any(name.startswith('tokenizer') or name.endswith('.model') for name in selected):
        raise ValueError('Official snapshot lacks tokenizer assets')
    return sorted(selected)


def verify_upstream_file(path, metadata):
    actual = sha256(path)
    lfs = getattr(metadata, 'lfs', None)
    expected = lfs.get('sha256') if isinstance(lfs, dict) else getattr(lfs, 'sha256', None)
    if expected:
        if actual != expected:
            raise ValueError('Upstream LFS SHA256 mismatch: '+metadata.rfilename)
        return actual, {'type': 'lfs-sha256', 'value': expected}
    blob = getattr(metadata, 'blob_id', None)
    if blob and re.fullmatch(r'[a-fA-F0-9]{40}', blob):
        digest = hashlib.sha1(b'blob '+str(path.stat().st_size).encode()+b'\0')
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024*1024), b''):
                digest.update(block)
        if digest.hexdigest() != blob.lower():
            raise ValueError('Upstream Git blob checksum mismatch: '+metadata.rfilename)
        return actual, {'type': 'git-blob-sha1', 'value': blob}
    raise ValueError('Missing authoritative upstream file checksum: '+metadata.rfilename)


def build(output, revision='main', maximum=CHUNK_BYTES):
    from huggingface_hub import HfApi, hf_hub_download, snapshot_download
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Build output must be a new directory')
    output.mkdir(parents=True)
    # Never authenticate to a private/gated repo; this job only republishes the
    # public upstream model, and never executes its repository code.
    api = HfApi(endpoint=ENDPOINT, token=False)
    info = api.model_info(REPOSITORY, revision=revision, files_metadata=True, token=False)
    if getattr(info, 'private', True) or getattr(info, 'gated', False):
        raise ValueError('Only the official public ungated model may be packaged')
    commit = str(info.sha or '')
    if not re.fullmatch(r'[a-fA-F0-9]{40}', commit):
        raise ValueError('Could not freeze an immutable official model revision')
    cache = output/'download-cache'
    readme_path = Path(hf_hub_download(REPOSITORY, 'README.md', revision=commit, cache_dir=str(cache), token=False, endpoint=ENDPOINT))
    evidence = declared_apache(info, readme_path.read_text(encoding='utf-8'))
    names = selected_files(info.siblings)
    source = Path(snapshot_download(REPOSITORY, revision=commit, cache_dir=str(cache), token=False,
                                    endpoint=ENDPOINT, allow_patterns=names, max_workers=2))
    stage, assets = output/FOLDER, output/'release-assets'
    stage.mkdir()
    metadata = {item.rfilename: item for item in info.siblings}
    records = []
    for name in names:
        original = (source/name).resolve(strict=True)
        actual, upstream = verify_upstream_file(original, metadata[name])
        target = stage/name
        try:
            os.link(original, target)  # real regular files, without another 4 GB copy
        except OSError:
            shutil.copy2(original, target)
        if target.is_symlink() or sha256(target) != actual:
            raise ValueError('Materialized model file differs from verified source: '+name)
        records.append({'name': name, 'sha256': actual, 'size': target.stat().st_size,
                        'source_url': ENDPOINT+'/'+REPOSITORY+'/resolve/'+commit+'/'+urllib.parse.quote(name),
                        'upstream_checksum': upstream})
    config = json.loads((stage/'config.json').read_text(encoding='utf-8'))
    if str(config.get('architecture', '')).lower() != 'voxcpm2':
        raise ValueError('Official configuration is not VoxCPM2')
    if not any(name.upper().startswith('LICENSE') for name in names):
        license_path = stage/'LICENSE-APACHE-2.0.txt'
        with urllib.request.urlopen(APACHE_URL, timeout=60) as response:
            license_bytes = response.read(1024*1024)
        if b'Apache License' not in license_bytes or b'Version 2.0' not in license_bytes or b'END OF TERMS AND CONDITIONS' not in license_bytes:
            raise ValueError('Invalid canonical Apache license response')
        license_path.write_bytes(license_bytes)
        records.append({'name': license_path.name, 'sha256': sha256(license_path), 'size': len(license_bytes), 'source_url': APACHE_URL})
    provenance = {'repository': REPOSITORY, 'revision': commit, 'license': 'apache-2.0',
                  'source_url': ENDPOINT+'/'+REPOSITORY+'/tree/'+commit, 'license_evidence': evidence,
                  'files': records, 'weights_and_config_unchanged': True,
                  'purpose': 'Public original model distribution only; no application or user data; no inference validation'}
    write_json(stage/'MODEL_PROVENANCE.json', provenance)
    assets.mkdir()
    archive = package_directory(stage, assets, 'VoxCPM2-original-'+commit[:12]+'.zip', maximum)
    manifest = {'format': 'voice-studio-modelpack-chunks-v1', 'repository': REPOSITORY, 'revision': commit,
                'license': 'apache-2.0', 'unpacked_root': FOLDER, 'archive': archive,
                'instructions': 'Download every chunk and this manifest together. Reassemble with the supplied standard-library Python helper, verify the archive SHA256, then extract all files.'}
    write_json(assets/'MODELPACK_MANIFEST.json', manifest)
    shutil.copy2(Path(__file__), assets/'REASSEMBLE_MODELPACK.py')
    (assets/'README_MODELPACK.txt').write_text('''PUBLIC ORIGINAL VOXCPM2 MODEL PACK

Only the official public Apache-2.0 model and its license/provenance are included.
No private voice recordings, application data, API keys or credentials are included.
This is model storage, not an application/runtime, and does not establish inference quality.

Download ALL .partNNN assets, MODELPACK_MANIFEST.json and REASSEMBLE_MODELPACK.py
into the same folder. Use Python 3.12 (or the Voice Studio bundled runtime):

python REASSEMBLE_MODELPACK.py --reassemble MODELPACK_MANIFEST.json --output VoxCPM2-original.zip

The helper verifies each chunk SHA256/size and the complete archive SHA256 before
leaving the assembled ZIP. Extract ALL files. The resulting voxcpm2-original folder
contains unchanged upstream config/weights and MODEL_PROVENANCE.json with the
official immutable revision and file hashes. CPU runtime preparation is separate.
''', encoding='utf-8')
    print('MODEL_PACK_READY '+json.dumps(manifest, ensure_ascii=False), flush=True)


def self_test():
    """Synthetic archive transport checks only, never a fake HF/license claim."""
    with tempfile.TemporaryDirectory(prefix='modelpack-test-') as directory:
        root = Path(directory)
        stage = root/'source';stage.mkdir()
        expected = bytes(range(256))*20
        (stage/'transport-test.bin').write_bytes(expected)
        assets = root/'assets'
        archive = package_directory(stage, assets, 'transport-test.zip', maximum=1000)
        assert len(archive['chunks']) > 1 and all(part['size'] <= 1000 for part in archive['chunks'])
        write_json(assets/'manifest.json', {'archive': archive})
        reassemble(assets/'manifest.json', root/'complete.zip')
        with zipfile.ZipFile(root/'complete.zip') as combined:
            assert combined.read(FOLDER+'/transport-test.bin') == expected
        first = assets/archive['chunks'][0]['name']
        contents = bytearray(first.read_bytes());contents[-1] ^= 1;first.write_bytes(contents)
        try:
            reassemble(assets/'manifest.json', root/'must-not-exist.zip')
        except ValueError as error:
            assert 'SHA256 mismatch' in str(error)
        else:
            raise AssertionError('Corrupted chunk was accepted')
        assert not (root/'must-not-exist.zip').exists()
        for name in ('../escape', '/absolute', 'root\\escape', 'C:escape'):
            try:safe_name(name)
            except ValueError:pass
            else:raise AssertionError('Unsafe manifest path accepted')
    print('PASS: split archive CRC, exact hash reassembly, corrupt chunk rejection and safe paths', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--revision', default='main')
    parser.add_argument('--chunk-bytes', type=int, default=CHUNK_BYTES)
    parser.add_argument('--reassemble', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
    elif args.reassemble:
        if args.output is None:parser.error('--output ZIP path is required for reassembly')
        reassemble(args.reassemble, args.output)
    else:
        if args.output is None:parser.error('--output NEW_DIRECTORY is required for a modelpack build')
        build(args.output, args.revision, args.chunk_bytes)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        message = (type(error).__name__+': '+str(error)).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print('::error title=Public VoxCPM2 modelpack failed::'+message, flush=True)
        raise
