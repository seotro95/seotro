import ctypes
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import pytest
import state_io

@pytest.mark.parametrize('code',[5,32])
def test_retry_temporary_windows_lock(tmp_path,monkeypatch,code):
    path=tmp_path/'progress.json';path.write_text('{"progress":41}')
    replace=Path.replace;attempts=[]
    def locked(source,target):
        attempts.append(source)
        if len(attempts)<3:
            error=PermissionError('Windows sharing lock');error.winerror=code;raise error
        return replace(source,target)
    monkeypatch.setattr(Path,'replace',locked);monkeypatch.setattr(state_io.time,'sleep',lambda _:None)
    assert state_io.write_progress(path,{'progress':75})
    assert json.loads(path.read_text())['progress']==75
    assert len(attempts)==3 and not list(tmp_path.glob('*.tmp'))


def test_persistent_lock_keeps_old_snapshot_but_durable_write_fails(tmp_path,monkeypatch):
    path=tmp_path/'progress.json';path.write_text('{"progress":41}')
    def locked(*args):raise PermissionError('Access denied')
    monkeypatch.setattr(Path,'replace',locked);monkeypatch.setattr(state_io.time,'sleep',lambda _:None)
    assert state_io.write_progress(path,{'progress':99}) is False
    assert json.loads(path.read_text())=={'progress':41}
    with pytest.raises(PermissionError):state_io.write_json_atomic(tmp_path/'result.json',{'progress':100})
    assert not list(tmp_path.glob('*.tmp'))


def test_video_output_completes_when_progress_is_locked(tmp_path,monkeypatch):
    from video_tasks import run
    from dubbing import inspect_video
    videos=tmp_path/'videos';videos.mkdir();work=tmp_path/'video_tasks'/'job';work.mkdir(parents=True)
    source=videos/'video.source'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=blue:s=160x90:r=10:d=1','-c:v','libx264','-f','mp4',str(source)],check=True)
    (videos/'video.json').write_text(json.dumps(inspect_video(source)))
    path=work/'job.json';path.write_text(json.dumps({'action':'render','video_id':'video','cues':[{'start':0,'end':1,'text':'Progress lock regression'}]}))
    progress=work/'progress.json';progress.write_text('{"progress":41}')
    replace=Path.replace
    def locked(source,target):
        if Path(target)==progress:raise PermissionError('Access denied to progress.json')
        return replace(source,target)
    monkeypatch.setattr(Path,'replace',locked)
    # These retries have deterministic locked outcomes; no real waiting is needed.
    monkeypatch.setattr(state_io.time,'sleep',lambda _:None)
    run(path)
    assert inspect_video(work/'output.mp4')['duration']>.9
    assert state_io.read_progress(progress)=={'progress':41}
    assert not list(work.glob('*.tmp'))


def test_completed_status_is_100_even_with_stale_or_invalid_progress(tmp_path,monkeypatch):
    import app
    monkeypatch.setattr(app,'DATA',tmp_path)
    ident='a'*32;work=tmp_path/'video_tasks'/ident;work.mkdir(parents=True)
    (work/'job.json').write_text(json.dumps({'video_id':'b'*32,'action':'render','status':'done'}))
    for text in ['{"progress":41}','broken JSON']:
        (work/'progress.json').write_text(text)
        result=app.video_task_status(ident)
        assert result['status']=='done' and result['progress']==100


def test_concurrent_writes_use_unique_tempfiles_and_whole_json(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    path=tmp_path/'job.json'
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda n:state_io.write_json_atomic(path,{'n':n,'payload':'x'*10000}),range(16)))
    assert len(json.loads(path.read_text())['payload'])==10000
    assert not list(tmp_path.glob('*.tmp'))


@pytest.mark.skipif(os.name!='nt',reason='Actual Windows sharing lock requires Win32')
def test_real_windows_read_handle_lock_is_retried(tmp_path):
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    kernel.CreateFileW.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
    path=tmp_path/'progress.json';path.write_text('{"progress":41}')
    # An ordinary reader permits reads/writes but blocks replacing the destination.
    handle=kernel.CreateFileW(str(path),0x80000000,0x1|0x2,None,3,0,None)
    assert handle not in (None,ctypes.c_void_p(-1).value)
    def release():time.sleep(.07);kernel.CloseHandle(handle)
    thread=threading.Thread(target=release);thread.start()
    try:assert state_io.write_progress(path,{'progress':100})
    finally:thread.join()
    assert state_io.read_progress(path)=={'progress':100}
