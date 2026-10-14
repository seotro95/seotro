import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import install_windows as setup


def info(version=(3, 11, 9), bits=64, path='C:\\Python311\\python.exe'):
    return {'executable':path,'version':list(version),'bits':bits,'platform':'win-amd64' if bits==64 else 'win32',
            'implementation':'cpython','free_threaded':False}


class WindowsSetupTests(unittest.TestCase):
    def test_uses_311_when_default_launcher_selects_315(self):
        calls=[]
        def probe(command):
            calls.append(command)
            if command==['C:\\Python311\\python.exe']:
                return info()
            if command==[setup.sys.executable]:
                return info((3,15,0),path='C:\\Python315\\python.exe')
            return None
        with patch.object(setup,'launcher_candidates',return_value=[['C:\\Python315\\python.exe'],['C:\\Python311\\python.exe']]), patch.object(setup.shutil,'which',return_value=None), patch.object(setup,'registry_candidates',return_value=[]), patch.object(setup,'probe',probe):
            chosen=setup.choose_python()
        self.assertEqual(chosen['version'][:2],[3,11])
        self.assertNotIn(['py','-3'],calls)

    def test_launcher_enumeration_keeps_spaces_and_never_requests_missing_runtime(self):
        listing=' -V:3.15 * C:\\Users\\Test User\\Python315\\python.exe\n -V:3.11 C:\\Program Files\\Python311\\python.exe\n'
        with patch.object(setup.shutil,'which',return_value='py.exe'),patch.object(setup.subprocess,'run',return_value=subprocess.CompletedProcess([],0,stdout=listing)) as run:
            paths=setup.launcher_candidates()
        self.assertEqual(paths,[['C:\\Users\\Test User\\Python315\\python.exe'],['C:\\Program Files\\Python311\\python.exe']])
        self.assertEqual(run.call_args.args[0],['py','-0p'])

    def test_rejects_315_32bit_arm_and_pypy(self):
        for candidate in [info((3,15,0)),info(bits=32),{**info(),'platform':'win-arm64'},
                          {**info(),'implementation':'pypy'},{**info(),'free_threaded':True}]:
            with self.subTest(candidate=candidate):
                self.assertFalse(setup.compatible(candidate))
        self.assertTrue(setup.compatible(info((3,12,10))))
        self.assertTrue(setup.compatible(info()))

    def test_missing_supported_python_does_not_touch_old_environment(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            old=root/'.venv';old.mkdir()
            (old/'custom.txt').write_text('preserve')
            with patch.object(setup,'ROOT',root),patch.object(setup,'choose_python',side_effect=ValueError('no compatible Python')):
                with self.assertRaises(ValueError):
                    setup.prepare_venv()
            self.assertEqual((old/'custom.txt').read_text(),'preserve')
            self.assertEqual(len(list(root.iterdir())),1)

    def test_incompatible_environment_is_backed_up_and_user_data_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            old=root/'.venv';(old/'Scripts').mkdir(parents=True)
            (old/'Scripts'/'python.exe').write_bytes(b'old interpreter')
            (old/'custom.txt').write_text('old packages and user notes')
            data=root/'data';data.mkdir();(data/'model.onnx').write_bytes(b'cached model')
            def probe(command):
                path=root/'.venv'/'Scripts'/'python.exe'
                return info((3,15,0)) if path.read_bytes()==b'old interpreter' else info()
            def create(command,**kwargs):
                self.assertEqual(command[0],info()['executable'])
                self.assertEqual(command[1:3],['-m','venv'])
                new=root/'.venv'/'Scripts';new.mkdir(parents=True)
                (new/'python.exe').write_bytes(b'supported interpreter')
                return subprocess.CompletedProcess(command,0)
            with patch.object(setup,'ROOT',root),patch.object(setup,'choose_python',return_value=info()),patch.object(setup,'probe',probe),patch.object(setup.subprocess,'run',create):
                python=setup.prepare_venv()
            self.assertEqual(python.read_bytes(),b'supported interpreter')
            backups=list(root.glob('.venv-backup-*'))
            self.assertEqual(len(backups),1)
            self.assertEqual((backups[0]/'custom.txt').read_text(),'old packages and user notes')
            self.assertEqual((data/'model.onnx').read_bytes(),b'cached model')

    def test_existing_supported_environment_is_reused_without_rebuild(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);python=root/'.venv'/'Scripts'/'python.exe'
            python.parent.mkdir(parents=True);python.write_bytes(b'valid')
            with patch.object(setup,'ROOT',root),patch.object(setup,'probe',return_value=info()),patch.object(setup.subprocess,'run',side_effect=AssertionError('must not rebuild')):
                self.assertEqual(setup.prepare_venv(),python)

    def test_dll_error_has_specific_repair_guidance(self):
        failed=subprocess.CompletedProcess([],1,stdout='',stderr='ImportError: DLL load failed: VCRUNTIME missing')
        with patch.object(setup.subprocess,'run',return_value=failed),self.assertRaisesRegex(ValueError,'Visual C\\+\\+'):
            setup.check_runtime(Path('python.exe'))


if __name__=='__main__':
    unittest.main()
