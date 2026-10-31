"""Verify cleaning boundaries, retained inference bytes and exact manifests."""
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile


SPEC = importlib.util.spec_from_file_location('clean_bundle', Path(__file__).with_name('build_clean_bundle.py'))
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def contents():
    files = {name: ('retained inference bytes: ' + name).encode('utf-8') for name in builder._REQUIRED}
    files['BUILD_INFO.json'] = json.dumps({'version':'1.12.1', 'encrypted_private_pack_bundled':True,
                                          'international_model_bundled':True, 'target_30x_guaranteed':False}).encode()
    files['MO_TOOL.bat'] = b'@echo off\r\ntitle Voice Studio Rieng 1.9.0 Portable\r\n"%~dp0runtime\\python.exe" app\\launcher.py\r\n'
    files['HUONG_DAN_CAN_MOC.txt'] = b'See PORTABLE-QA.json\n'
    files['requirements-runtime.txt'] = b'numpy==0.0.1\n'
    files.update({
        'runtime/Lib/site-packages/numpy-2.0.0.dist-info/METADATA':b'Metadata-Version: 2.1\nName: numpy\nVersion: 2.0.0\n\n',
        'runtime/Lib/site-packages/numpy-2.0.0.dist-info/licenses/LICENSE.txt':b'Important license',
        'runtime/Lib/site-packages/numpy/testing/helper.py':b'required helper',
        'runtime/Lib/site-packages/scipy/_lib/_testutils.py':b'required helper',
        'runtime/Lib/site-packages/scipy.whl':b'not the audited placeholder',
        'runtime/Lib/ensurepip/_bundled/pip.whl':b'required optional installer',
        'runtime/Lib/site-packages/gradio/front/app.js':b'needed JS data',
        'runtime/Lib/site-packages/gradio/front/app.js.map':b'removable source map',
        'runtime/Lib/site-packages/other/data.map':b'needed map data',
        'runtime/Lib/test/test_audio.py':b'unused unit test',
        'runtime/Lib/idlelib/idle_test/test_run.py':b'unused IDLE test',
        'runtime/Doc/html/index.html':b'offline documentation',
        'runtime/python-3.12.10-amd64.exe':b'redundant installer',
        'runtime/Lib/site-packages/scipy-1.18.1-cp312-cp312-win_amd64.whl':b'',
        'BASE-1.10-MANIFEST.sha256':b'old manifest',
        'BASE-1.10-BUILD_INFO.json':b'keep provenance',
        'BASE-MODEL-APACHE-2.0-LICENSE.txt':b'keep model license',
        'CPU-SHORT-SPEECH-BENCHMARK.json':b'old benchmark',
        'DOC_TRUOC.md':b'outdated README',
        'DOC_TRUOC_FULL.txt':b'duplicate old guide',
        'README_GITHUB_19_GIONG.txt':b'outdated README',
    })
    files['MANIFEST.sha256'] = ''.join(digest(value)+'  '+name+'\n'
                                      for name,value in sorted(files.items()) if name!='MANIFEST.sha256').encode()
    return files


def write_source(path, files, *, extra=None):
    with zipfile.ZipFile(path, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name,value in files.items(): archive.writestr(builder.SOURCE_NAME+'/'+name,value)
        if extra is not None:
            name, value, mode = extra
            info=zipfile.ZipInfo(name)
            info.external_attr=mode<<16
            archive.writestr(info,value)
    return builder.file_sha256(path)


def read_clean(path):
    with zipfile.ZipFile(path) as archive:
        return {info.filename.split('/',1)[1]:archive.read(info) for info in archive.infolist()}


class CleanBundleTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.source,self.output=self.root/'source.zip',self.root/'clean.zip'

    def build(self, files=None):
        original=files or contents()
        sha=write_source(self.source,original)
        builder.build_clean(self.source,self.output,_expected_sha256=sha)
        return original,read_clean(self.output)

    def test_clean_retains_all_inference_and_license_bytes(self):
        original,result=self.build()
        for name,value in original.items():
            if builder._protected(name) or '.dist-info/' in name or name.endswith('LICENSE.txt'):
                self.assertEqual(result[name],value,name)
        for name in ('runtime/Lib/site-packages/numpy/testing/helper.py',
                     'runtime/Lib/site-packages/scipy/_lib/_testutils.py',
                     'runtime/Lib/ensurepip/_bundled/pip.whl',
                     'runtime/Lib/site-packages/gradio/front/app.js',
                     'runtime/Lib/site-packages/other/data.map'):
            self.assertEqual(result[name],original[name])
        for name,value in original.items():
            if builder.removal_reason(name,len(value)):self.assertNotIn(name,result)
        self.assertIn(b'1.12.1 Clean Portable',result['MO_TOOL.bat'])
        self.assertNotIn(b'1.9.0',result['MO_TOOL.bat'])
        self.assertIn(b'WINDOWS-NATIVE-VOXCPM-QA.json',result['HUONG_DAN_CAN_MOC.txt'])

    def test_new_manifest_covers_exact_output_and_report_covers_exact_removals(self):
        original,result=self.build()
        records={line[66:]:line[:64] for line in result['MANIFEST.sha256'].decode().splitlines()}
        self.assertEqual(set(records),set(result)-{'MANIFEST.sha256'})
        for name,value in result.items():
            if name!='MANIFEST.sha256':self.assertEqual(records[name],digest(value))
        report=json.loads(result['CLEANUP-REPORT.json'])
        expected={name for name,value in original.items() if builder.removal_reason(name,len(value))}
        self.assertEqual({row['path'] for row in report['removed_files']},expected)
        self.assertEqual(report['removed_file_count'],len(expected))
        self.assertEqual(report['removed_uncompressed_bytes'],sum(len(original[name]) for name in expected))
        self.assertTrue(report['all_source_files_sha256_verified'])
        self.assertEqual(report['windows_clean_package_qa'],'not_run')
        info=json.loads(result['BUILD_INFO.json'])
        self.assertEqual(info['version'],'1.12.1')
        self.assertEqual(info['package_revision'],'clean-1')
        self.assertEqual(info['cleaned_windows_package_qa'],'not_run')
        checksum=Path(str(self.output)+'.sha256').read_text().split()[0]
        self.assertEqual(checksum,builder.file_sha256(self.output))

    def test_actual_inventory_does_not_copy_stale_recipe_versions(self):
        original,result=self.build()
        self.assertIn(b'numpy==2.0.0\n',result['BUNDLED-PACKAGES.txt'])
        self.assertNotIn(b'numpy==0.0.1',result['BUNDLED-PACKAGES.txt'])
        self.assertTrue(result['requirements-runtime.txt'].endswith(original['requirements-runtime.txt']))
        self.assertIn('Chưa xác minh suy luận GPU',result['DOC_TRUOC.txt'].decode())
        self.assertIn('việc dọn tệp không tự làm tốc độ suy luận nhanh hơn',result['DOC_TRUOC.txt'].decode())

    def test_manifest_mismatch_rejects_even_removed_file_and_leaves_no_output(self):
        files=contents()
        files['runtime/Lib/test/test_audio.py']=b'modified after manifest'
        sha=write_source(self.source,files)
        with self.assertRaisesRegex(ValueError,'SHA256 mismatch'):
            builder.build_clean(self.source,self.output,_expected_sha256=sha)
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob('*.assembling*')))

    def test_wrong_source_pin_and_existing_outputs_are_preserved(self):
        sha=write_source(self.source,contents())
        with self.assertRaisesRegex(ValueError,'Pinned full source ZIP'):
            builder.build_clean(self.source,self.output)
        self.output.write_bytes(b'user file')
        with self.assertRaises(FileExistsError):builder.build_clean(self.source,self.output,_expected_sha256=sha)
        self.assertEqual(self.output.read_bytes(),b'user file')
        self.output.unlink()
        sidecar=Path(str(self.output)+'.sha256');sidecar.write_bytes(b'user checksum')
        with self.assertRaises(FileExistsError):builder.build_clean(self.source,self.output,_expected_sha256=sha)
        self.assertEqual(sidecar.read_bytes(),b'user checksum')
        self.assertFalse(self.output.exists())

    def test_unsafe_members_and_windows_case_collisions_are_rejected(self):
        cases=[('../escape',stat.S_IFREG), (builder.SOURCE_NAME+'/../escape',stat.S_IFREG),
               (builder.SOURCE_NAME+'/runtime/./unsafe',stat.S_IFREG),
               (builder.SOURCE_NAME+'/runtime/CON.txt',stat.S_IFREG),
               (builder.SOURCE_NAME+'/runtime/link',stat.S_IFLNK),
               (builder.SOURCE_NAME+'/runtime/PYTHON.EXE',stat.S_IFREG)]
        for number,(name,mode) in enumerate(cases):
            with self.subTest(name=name):
                source=self.root/f'bad-{number}.zip'
                sha=write_source(source,contents(),extra=(name,b'unsafe',mode|0o644))
                with self.assertRaises(ValueError):builder.build_clean(source,self.output,_expected_sha256=sha)
                self.assertFalse(self.output.exists())

    def test_removal_policy_preserves_unlisted_data_and_installed_dependencies(self):
        for name in ('runtime/Lib/site-packages/ruff/__main__.py',
                     'runtime/Lib/site-packages/pytest/__init__.py',
                     'runtime/Lib/site-packages/scipy/testing.py',
                     'runtime/Lib/site-packages/gradio/data.map',
                     'runtime/Lib/site-packages/not-gradio/app.js.map',
                     'app/.data/models/cache/hub/.no_exist',
                     'app/.data/models/voxcpm2-native/voxcpm2-q8_0.gguf',
                     'CPU-NEW-CURRENT-DIAGNOSTIC.json'):
            self.assertIsNone(builder.removal_reason(name,0),name)
        self.assertIsNone(builder.removal_reason('runtime/Lib/site-packages/scipy-1.18.1-cp312-cp312-win_amd64.whl',10))


if __name__=='__main__':unittest.main()
