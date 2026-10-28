"""Run the real unlock script against encrypted synthetic legacy updaters.

The reference archive deliberately contains 1.7 application files while the
installed target is 1.8. No user recordings or private delivery keys are used.
"""
from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shlex
import shutil
import struct
import subprocess
import sys
import zipfile

import pytest


PACKAGING = Path(__file__).resolve().parent
SCRIPT = PACKAGING/'github-delivery/install_secure_voices.ps1'
PASSWORD = 'voice-studio-synthetic-test-only'
UPDATER_ROOT = 'Voice-Studio-Rieng-1.7.0-Cap-Nhat-19-Giong'

SPEC = importlib.util.spec_from_file_location('unlock_synthetic_support', PACKAGING/'test_install_voice_update.py')
support = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(support)


def powershell():
    candidates = [shutil.which('powershell.exe'), shutil.which('pwsh')]
    if os.name != 'nt':
        candidates.append('/workspace/runtime/pwsh-diagnostic/pwsh')
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    pytest.skip('PowerShell is required for the actual unlock regression')


def embedded_python(runtime):
    runtime.mkdir(parents=True)
    target = runtime/'python.exe'
    if os.name == 'nt':
        # A minimal temporary venv uses the already-tested interpreter's stdlib.
        # It executes only the standard-library updater, not a TTS dependency.
        shutil.copy2(sys.executable, target)
        home = Path(sys.base_prefix)
        for dll in home.glob('python*.dll'):
            shutil.copy2(dll, runtime/dll.name)
        (runtime/'pyvenv.cfg').write_text(
            f'home = {home}\ninclude-system-site-packages = false\n', encoding='utf-8')
    else:
        target.write_text('#!/bin/sh\nexec '+shlex.quote(sys.executable)+' "$@"\n', encoding='utf-8')
        target.chmod(0o700)
    return target


def encrypted_package(source, package):
    crypto = pytest.importorskip('cryptography.hazmat.primitives.ciphers')
    padding = pytest.importorskip('cryptography.hazmat.primitives.padding')
    plain_zip = source.parent/'synthetic-legacy-update.zip'
    with zipfile.ZipFile(plain_zip, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(source.rglob('*')):
            if file.is_file():
                archive.write(file, UPDATER_ROOT+'/'+file.relative_to(source).as_posix())
    plain = plain_zip.read_bytes()
    salt, iv = secrets.token_bytes(16), secrets.token_bytes(16)
    keys = hashlib.pbkdf2_hmac('sha256', PASSWORD.encode(), salt, 200000, 64)
    header = b'VSPACK01'+salt+iv+struct.pack('<Q', len(plain))
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plain)+padder.finalize()
    encryptor = crypto.Cipher(crypto.algorithms.AES(keys[:32]), crypto.modes.CBC(iv)).encryptor()
    ciphertext = encryptor.update(padded)+encryptor.finalize()
    packet = header+ciphertext+hmac.digest(keys[32:], header+ciphertext, 'sha256')
    delivery = package/'delivery'
    delivery.mkdir(parents=True)
    (delivery/'voices.vspack').write_bytes(packet)
    (delivery/'manifest.json').write_text(json.dumps({
        'format': 'voice-studio-private-delivery-v1', 'encrypted_file': 'voices.vspack',
        'encrypted_size': len(packet), 'encrypted_sha256': hashlib.sha256(packet).hexdigest(),
        'plaintext_size': len(plain), 'plaintext_sha256': hashlib.sha256(plain).hexdigest(),
        'updater_root': UPDATER_ROOT,
    }), encoding='utf-8')


@pytest.fixture
def legacy_unlock(tmp_path):
    powershell_path = powershell()
    target = tmp_path/'installed 1.8 é'
    embedded_python(target/'runtime')
    current = {
        'app/app.py': b"VERSION = '1.8.0'\n",
        'app/worker.py': b'new parallel cue renderer\n',
        'app/voxcpm_acceleration.py': b'new reference and active KV cache\n',
        'MO_TOOL.bat': b'current 1.8 launcher\r\n',
        'BUILD_INFO.json': b'{"version":"1.8.0"}\n',
        'app/.data/jobs/history.json': b'private history kept\n',
        'app/.data/models/existing.ready': b'existing model kept\n',
        'runtime-international/python.exe': b'existing international runtime kept\n',
    }
    for name, value in current.items():
        path = target/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    legacy = tmp_path/'legacy update'
    (legacy/'payload/app').mkdir(parents=True)
    (legacy/'payload/app/app.py').write_bytes(b"VERSION = '1.7.0'\n")
    (legacy/'payload/app/worker.py').write_bytes(b'old sequential renderer\n')
    (legacy/'payload/MO_TOOL.bat').write_bytes(b'old launcher\r\n')
    (legacy/'payload/BUILD_INFO.json').write_bytes(b'{"version":"1.7.0"}\n')
    shutil.copy2(PACKAGING/'install_voice_update.py', legacy/'install_update.py')
    languages = ('en-US', 'ko', 'ru', 'ja', 'fr', 'es', 'th')
    voices = [support.synthetic_voice(legacy/'voice-pack', f'{index:032x}',
                                     languages[(index-1) % len(languages)])
              for index in range(1, 20)]
    support.write_manifest(legacy/'voice-pack/manifest.json', voices)
    return tmp_path, powershell_path, target, legacy, current, voices


def unlock(fixture, package):
    temporary, powershell_path, target, _, _, _ = fixture
    env = dict(os.environ)
    # Keep shell diagnostic caches local; no actual private password is read.
    env.update(XDG_CACHE_HOME=str(temporary/'cache'), XDG_CONFIG_HOME=str(temporary/'config'),
               XDG_DATA_HOME=str(temporary/'data'))
    env['PATH'] = str(Path(sys.executable).parent)+os.pathsep+env.get('PATH', '')
    return subprocess.run([
        powershell_path, '-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', str(SCRIPT), '-PackageRoot', str(package), '-Target', str(target),
        '-Password', PASSWORD,
    ], env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)


def test_actual_unlock_preserves_new_application_and_installs_all_references(legacy_unlock):
    temporary, _, target, legacy, before, voices = legacy_unlock
    package = temporary/'encrypted download'
    encrypted_package(legacy, package)
    first = unlock(legacy_unlock, package)
    assert first.returncode == 0, first.stdout+'\n'+first.stderr
    for relative, value in before.items():
        assert (target/relative).read_bytes() == value, relative
    library = target/'app/voice-library'
    catalog = json.loads((library/'manifest.json').read_text(encoding='utf-8'))
    assert len(catalog['voices']) == 19
    assert {record['id'] for record in catalog['voices']} == {record['id'] for record in voices}
    for voice in voices:
        assert support.digest(library/voice['reference_audio']) == voice['reference_sha256']
        assert support.digest(library/voice['original_audio']) == voice['source_sha256']
    journals = list((target/'update-backups').glob('*/journal.json'))
    assert len(journals) == 1
    paths = {record['path'] for record in json.loads(journals[0].read_text())['files']}
    assert all(path.startswith('app/voice-library/') for path in paths)
    second = unlock(legacy_unlock, package)
    assert second.returncode == 0, second.stdout+'\n'+second.stderr
    assert len(list((target/'update-backups').glob('*/journal.json'))) == 1
    assert not list(target.glob('.voice-install-*'))
    for relative, value in before.items():
        assert (target/relative).read_bytes() == value, relative


def test_actual_unlock_rejects_tampered_voice_without_downgrading_or_leaking_temp(legacy_unlock):
    temporary, _, target, legacy, before, voices = legacy_unlock
    reference = legacy/'voice-pack'/voices[0]['reference_audio']
    reference.write_bytes(reference.read_bytes()+b'tampered synthetic bytes')
    package = temporary/'bad encrypted download'
    encrypted_package(legacy, package)
    result = unlock(legacy_unlock, package)
    assert result.returncode != 0
    for relative, value in before.items():
        assert (target/relative).read_bytes() == value, relative
    assert not (target/'app/voice-library').exists()
    assert not (target/'update-backups').exists()
    assert not list(target.glob('.voice-install-*'))
