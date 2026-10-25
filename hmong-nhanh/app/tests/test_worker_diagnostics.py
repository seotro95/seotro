import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import cloning_engine
import voice_worker


@pytest.mark.parametrize('exception,expected', [
    (MemoryError('private script'), 'RAM'),
    (RuntimeError('CUDA out of memory: secret transcript'), 'bộ nhớ GPU'),
    (ImportError('DLL load failed: private/path'), 'Windows'),
    (ModuleNotFoundError('private_module'), 'Thiếu thư viện'),
    (RuntimeError('CUDA no kernel image private details'), 'GPU'),
    (PermissionError('private/path'), 'quyền'),
    (RuntimeError('secret transcript unknown'), 'worker.log'),
])
def test_runtime_error_diagnostics_do_not_expose_exception_payload(exception,expected):
    message=cloning_engine._inference_error_message(exception)
    assert expected in message
    for private in ('private/path','private_module','secret transcript','private script'):
        assert private not in message


def test_utf8_job_path_and_vietnamese_reply_work_with_ascii_console(tmp_path):
    folder=tmp_path/'Bản đọc giọng ngoài';folder.mkdir();(folder/'input.json').write_text('{}')
    fake=tmp_path/'modules';fake.mkdir()
    (fake/'longform.py').write_text("def process_job(folder):\n    (folder/'visited').write_text('ok')\n    raise ValueError('Mẫu giọng chưa sẵn sàng')\n",encoding='utf-8')
    (fake/'cloning_engine.py').write_text('class CloningError(Exception): pass\n')
    script='import sys,importlib.util;sys.path.insert(0,sys.argv[1]);s=importlib.util.spec_from_file_location("worker",sys.argv[2]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.serve()'
    env={**os.environ,'PYTHONIOENCODING':'ascii','PYTHONUTF8':'0'}
    output=subprocess.run([sys.executable,'-c',script,str(fake),voice_worker.__file__],
        input=(json.dumps({'folder':str(folder)},ensure_ascii=False)+'\n').encode('utf-8'),
        capture_output=True,env=env,timeout=10,check=True)
    reply=json.loads(output.stdout.decode('ascii'))
    assert reply=={'ok':False,'error':'Mẫu giọng chưa sẵn sàng'}
    assert (folder/'visited').read_text()=='ok'
