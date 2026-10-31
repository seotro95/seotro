"""Download metadata boundaries and Windows join/restart tests (no network)."""
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile


SPEC = importlib.util.spec_from_file_location('one_click_download', Path(__file__).with_name('build_one_click_download.py'))
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def fixture():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        archive.writestr('example.txt', 'Verified full download fixture')
    payload = stream.getvalue()
    pieces = (payload[:40], payload[40:80], payload[80:])
    name = 'Fixture-Full-Windows-x64.zip'
    manifest = {
        'format': 'voice-studio-full-zip-parts-v1', 'archive': name,
        'archive_size': len(payload), 'archive_sha256': hashlib.sha256(payload).hexdigest(),
        'parts': [{'name': name + f'.part{index:03d}', 'size': len(piece),
                   'sha256': hashlib.sha256(piece).hexdigest()}
                  for index, piece in enumerate(pieces, 1)],
    }
    return manifest, payload, pieces


class GeneratorTests(unittest.TestCase):
    def test_payload_pins_all_bytes_and_is_readable_ascii_crlf(self):
        manifest, _, _ = fixture()
        payload = builder.make_script(manifest)
        text = payload.decode('ascii')
        self.assertNotIn(b'\n', payload.replace(b'\r\n', b''))
        self.assertIn(f'set "VS_FULL_SHA={manifest["archive_sha256"]}"', text)
        for index, part in enumerate(manifest['parts'], 1):
            self.assertIn(f'call :part "{part["name"]}" "{part["size"]}" "{part["sha256"]}" "{index:03d}"', text)
        self.assertIn('copy /b "%VS_SOURCE_001%"+"%VS_SOURCE_002%"+"%VS_SOURCE_003%"', text)
        self.assertIn('VOICE_DOWNLOAD_NO_PAUSE', text)

    def test_shell_filenames_and_bad_metadata_are_rejected(self):
        manifest, _, _ = fixture()
        for name in ('../escape.zip', 'A&run.zip', 'A%PATH%.zip', 'A!run.zip', 'A\nrun.zip',
                     'C:\\escape.zip', 'CON.zip', 'lpt1.other.zip', 'unicode-\u1ec7.zip'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                builder.make_script({**manifest, 'archive': name})
        for field, value in (('archive_size', True), ('archive_size', 0), ('archive_sha256', 'f' * 63)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                builder.make_script({**manifest, field: value})

    def test_parts_need_order_exact_names_hashes_and_total(self):
        manifest, _, _ = fixture()
        for case in ('order', 'size', 'hash', 'name', 'sum', 'empty'):
            data = copy.deepcopy(manifest)
            if case == 'order': data['parts'].reverse()
            if case == 'size': data['parts'][0]['size'] = 2 * 1024**3
            if case == 'hash': data['parts'][0]['sha256'] = 'xyz'
            if case == 'name': data['parts'][0]['name'] = 'https://attacker.invalid/part'
            if case == 'sum': data['archive_size'] += 1
            if case == 'empty': data['parts'] = []
            with self.subTest(case=case), self.assertRaises(ValueError):
                builder.make_script(data)

    def test_urls_cannot_change_host_protocol_or_inject_commands(self):
        manifest, _, _ = fixture()
        urls = (
            builder.DEFAULT_BASE.replace('https:', 'http:'),
            builder.DEFAULT_BASE.replace('github.com', 'attacker.invalid'),
            builder.DEFAULT_BASE.replace('github.com', 'user@github.com'),
            builder.DEFAULT_BASE + '?download=1', builder.DEFAULT_BASE + '#fragment',
            builder.DEFAULT_BASE + '\ncalc.exe',
            builder.DEFAULT_BASE.replace('github.com', 'git\nhub.com'),
            builder.DEFAULT_BASE.replace('github.com', 'git\rhub.com'),
            builder.DEFAULT_BASE.replace('github.com', 'git\thub.com'),
            builder.DEFAULT_BASE.replace('seotro95/seotro', 'other/repository'),
        )
        for value in urls:
            with self.subTest(url=value), self.assertRaises(ValueError):
                builder.make_script(manifest, value)

    def test_transport_keeps_certificate_checks_and_never_runs_the_download(self):
        manifest, _, _ = fixture()
        text = builder.make_script(manifest).decode('ascii')
        self.assertIn('--proto "=https" --proto-redir "=https"', text)
        self.assertIn('--continue-at -', text)
        self.assertIn('[Net.SecurityProtocolType]::Tls12', text)
        self.assertIn('[Security.Cryptography.SHA256]::Create()', text)
        self.assertIn('$h.ComputeHash($s)', text)
        self.assertNotIn('Get-FileHash', text, 'Hashing must work without optional PowerShell modules')
        for forbidden in ('EncodedCommand', 'ExecutionPolicy', 'ScriptBlock', 'ServerCertificateValidationCallback',
                          'Invoke-Expression', 'Start-Process', ' --insecure', ' -k ', ' -SkipCertificateCheck'):
            self.assertNotIn(forbidden.lower(), text.lower())
        self.assertEqual([line for line in text.splitlines() if 'MO_TOOL' in line],
                         ['echo Giai nen toan bo ZIP vao thu muc moi. Sau do mo MO_TOOL.bat.'])

    def test_build_preserves_existing_output_and_rejects_unbounded_input(self):
        manifest, _, _ = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, target = root/'manifest.json', root/'download.cmd'
            source.write_text(json.dumps(manifest), encoding='utf-8')
            builder.build(source, target)
            original = target.read_bytes()
            with self.assertRaises(FileExistsError): builder.build(source, target)
            self.assertEqual(target.read_bytes(), original)
            source.write_bytes(b' ' * 65537)
            with self.assertRaises(ValueError): builder.build(source, root/'other.cmd')
            self.assertFalse((root/'other.cmd').exists())


@unittest.skipUnless(os.name == 'nt', 'Actual CMD and Windows PowerShell required')
class WindowsRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)/'tai ve \u1ec7 & 50% !'
        self.root.mkdir()
        self.manifest, self.payload, self.pieces = fixture()
        self.script = self.root/builder.OUTPUT_NAME
        self.script.write_bytes(builder.make_script(self.manifest))
        self.cache = self.root/('_Voice-Studio-Download-' + self.manifest['archive_sha256'][:12])
        self.archive = self.root/self.manifest['archive']

    def run_command(self):
        env = {**os.environ, 'VOICE_DOWNLOAD_NO_PAUSE': '1'}
        result = subprocess.run(['cmd.exe', '/d', '/c', self.script.name], cwd=self.root,
                                env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
        return result.returncode, result.stdout.decode(errors='replace')

    def seed_near(self):
        for part, piece in zip(self.manifest['parts'], self.pieces):
            (self.root/part['name']).write_bytes(piece)

    def seed_cache(self):
        self.cache.mkdir()
        (self.cache/'OWNER.txt').write_text('voice-studio-download-v1 ' + self.manifest['archive_sha256'], encoding='ascii')

    def test_unicode_and_shell_characters_join_then_reuse_final_zip(self):
        self.seed_near()
        code, output = self.run_command()
        self.assertEqual(code, 0, output)
        self.assertEqual(self.archive.read_bytes(), self.payload)
        for part, piece in zip(self.manifest['parts'], self.pieces):
            self.assertEqual((self.root/part['name']).read_bytes(), piece)
        for file in self.cache.iterdir(): file.unlink()
        self.cache.rmdir()
        code, output = self.run_command()
        self.assertEqual(code, 0, output)
        self.assertFalse(self.cache.exists(), 'Valid full ZIP should avoid downloads and cache work')

    def test_existing_different_zip_is_preserved(self):
        self.archive.write_bytes(b'user existing ZIP')
        code, output = self.run_command()
        self.assertNotEqual(code, 0, output)
        self.assertEqual(self.archive.read_bytes(), b'user existing ZIP')
        self.assertFalse(self.cache.exists())

    def test_unowned_cache_is_preserved(self):
        self.cache.mkdir()
        sentinel = self.cache/'private.txt'
        sentinel.write_bytes(b'user data')
        self.seed_near()
        code, output = self.run_command()
        self.assertNotEqual(code, 0, output)
        self.assertEqual(sentinel.read_bytes(), b'user data')
        self.assertFalse((self.cache/'OWNER.txt').exists())
        self.assertFalse(self.archive.exists())

    def test_completed_partial_and_verified_cache_parts_are_reused(self):
        self.seed_cache()
        for index, (part, piece) in enumerate(zip(self.manifest['parts'], self.pieces)):
            suffix = '.partial' if index == 0 else ''
            (self.cache/(part['name'] + suffix)).write_bytes(piece)
        code, output = self.run_command()
        self.assertEqual(code, 0, output)
        self.assertEqual(self.archive.read_bytes(), self.payload)
        self.assertFalse(list(self.cache.glob('*.partial')))

    def test_corrupt_completed_cache_part_is_preserved(self):
        self.seed_cache()
        part = self.cache/self.manifest['parts'][0]['name']
        part.write_bytes(b'existing corrupt cache item')
        code, output = self.run_command()
        self.assertNotEqual(code, 0, output)
        self.assertEqual(part.read_bytes(), b'existing corrupt cache item')
        self.assertFalse(self.archive.exists())


if __name__ == '__main__': unittest.main()
