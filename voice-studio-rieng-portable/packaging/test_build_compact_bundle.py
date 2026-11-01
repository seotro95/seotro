import hashlib
import json
from pathlib import Path
import zipfile

import pytest

import build_compact_bundle as builder


def fixture(tmp_path, extra=None):
    source = tmp_path/'source'
    (source/'app/static').mkdir(parents=True)
    (source/'packaging').mkdir()
    (source/'app/app.py').write_bytes(b'CURRENT_APPLICATION=True\n')
    (source/'app/static/app.js').write_bytes(b'current_script();')
    (source/'packaging/MO_TOOL.bat').write_bytes(b'current launcher')
    payloads = {name: ('fixture '+name).encode() for name in builder.REQUIRED}
    payloads['BUILD_INFO.json'] = json.dumps({'encrypted_private_voice_count':19,
        'native_windows_offline_smoke':'passed'}).encode()
    payloads.update({'app/app.py':b'old source', 'runtime/Doc/manual.txt':b'unused manual',
                     'MANIFEST.sha256':b'old manifest'})
    payloads.update(extra or {})
    archive = tmp_path/'original.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        for name, data in payloads.items(): z.writestr('Original/'+name, data)
    return source, archive, builder.sha(archive), payloads


def test_preserves_runtime_models_and_encrypted_pack_and_replaces_app(tmp_path):
    source, original, digest, files = fixture(tmp_path)
    output = tmp_path/'compact.zip'
    report = builder.build(original, output, source=source, expected=digest)
    assert report['private_pack_preserved'] and report['windows_tested'] is False
    assert builder.sha(original) == digest
    with zipfile.ZipFile(output) as z:
        read = lambda name: z.read(builder.ROOT+'/'+name)
        for name in builder.REQUIRED-{'BUILD_INFO.json'}: assert read(name) == files[name]
        assert read('app/app.py') == b'CURRENT_APPLICATION=True\n'
        assert builder.ROOT+'/runtime/Doc/manual.txt' not in z.namelist()
        record = json.loads(read('BUILD_INFO.json'))
        assert record['current_windows_validation'] == 'not_run'
        assert record['private_voice_unlock_tested'] is False
        assert record['inherited_private_voice_count'] == 19
        for line in read('MANIFEST.sha256').decode().splitlines():
            expected, name = line.split('  ',1)
            assert hashlib.sha256(read(name)).hexdigest() == expected


def test_wrong_archive_is_rejected_and_existing_output_is_preserved(tmp_path):
    source, original, digest, _ = fixture(tmp_path)
    output = tmp_path/'compact.zip'
    with pytest.raises(ValueError, match='SHA256'):
        builder.build(original, output, source=source, expected='0'*64)
    assert not output.exists()
    output.write_bytes(b'existing user file')
    with pytest.raises(FileExistsError): builder.build(original, output, source=source, expected=digest)
    assert output.read_bytes() == b'existing user file'


def test_traversal_and_incomplete_packages_never_produce_a_distribution(tmp_path):
    source, original, digest, _ = fixture(tmp_path, {'../outside.exe':b'untrusted'})
    output = tmp_path/'compact.zip'
    with pytest.raises(ValueError, match='Unsafe'):
        builder.build(original, output, source=source, expected=digest)
    assert not output.exists()
    assert not output.with_suffix('.building').exists()
