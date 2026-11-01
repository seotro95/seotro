import argparse,hashlib,json,os,subprocess,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent

def main(archive,destination):
    archive=Path(archive);destination=Path(destination);destination.mkdir(exist_ok=True)
    expected=json.loads((HERE/'expected-assets.json').read_text())[archive.name]
    with archive.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==expected['sha256']
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            assert (destination/info.filename).resolve().is_relative_to(destination.resolve())
        z.extractall(destination)
    root=destination/'Voice-Studio-1.13.0-Online19-Windows'
    data=destination/'test-data'
    env=dict(os.environ,PYTHONHOME='',PYTHONPATH='',PYTHONNOUSERSITE='1',PYTHONUTF8='1',
             VOICE_STUDIO_DATA_DIR=str(data),OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
             PATH=str(root/'ffmpeg/bin')+os.pathsep+str(root/'runtime')+os.pathsep+os.environ['PATH'])
    env.pop('AZURE_SPEECH_KEY',None);env.pop('AZURE_SPEECH_REGION',None)
    report=destination/'WINDOWS-QA.json'
    subprocess.run([str(root/'runtime/python.exe'),'-s','-X','utf8',str(HERE/'windows_runtime_qa.py'),
                    '--root',str(root),'--report',str(report)],env=env,check=True,timeout=180)
    assert json.loads(report.read_text())==json.loads((HERE/'windows-expected.json').read_text())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive');p.add_argument('destination');a=p.parse_args();main(a.archive,a.destination)
