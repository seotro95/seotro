import hashlib,json,os,shutil,subprocess,sys,urllib.request
from pathlib import Path
work=Path('build').resolve();work.mkdir(exist_ok=True);tool=work/'melo-tool';tool.mkdir(exist_ok=True)
config=json.loads(Path('input/source_integrity.json').read_text())
if not shutil.which('ffmpeg'):
    subprocess.run(['sudo','apt-get','update'],check=True)
    subprocess.run(['sudo','apt-get','install','--no-install-recommends','-y','ffmpeg'],check=True)
for name,record in config.items():
    data=urllib.request.urlopen(record['url'],timeout=60).read()
    assert hashlib.sha256(data).hexdigest()==record['sha256'],name
    (tool/name).write_bytes(data)
for name in ['render_common.py','render_online.py','prosody.py']:
    shutil.copy(Path('scripts')/name,work/name)
shutil.copy('input/BASELINE_VOICE_PROFILES.json',work/'BASELINE_VOICE_PROFILES.json')
shutil.copy('input/DOCUMENT_DELIVERY_STATE.json',work/'DOCUMENT_DELIVERY_STATE.json')
dest=work/'voice/scripts';dest.mkdir(parents=True,exist_ok=True)
for p in Path('input/scripts').glob('*'):
    if p.is_file():shutil.copy(p,dest/p.name)
env=os.environ.copy();env['PRODUCTION_WORK_DIR']=str(work);env['MELO_TOOL_DIR']=str(tool)
env['MELO_VIET_ROOT']=str(work/'melo-data')
locale=sys.argv[1];mode=sys.argv[2]
if mode=='smoke':
    code="""import json,sys,wave
from pathlib import Path
sys.path.insert(0,str(Path('build/melo-tool').resolve()))
import online_backend
rows=json.loads(Path('input/scripts/en-US.json').read_text())
result=online_backend.handle({'op':'render','language':'en-US','voice':'en-US-AndrewNeural','text':rows[0]['voice'],'output':'build/smoke.wav'})
assert result['audio_seconds']>1
print(json.dumps({'smoke':'passed','voice':result['voice'],'seconds':result['audio_seconds']}))
"""
    subprocess.run([sys.executable,'-c',code],env=env,check=True)
elif mode=='preview':
    p=dest/'en-US.json';rows=json.loads(p.read_text())[:3];p.write_text(json.dumps(rows,ensure_ascii=False))
    env['PRODUCTION_TARGET_SECONDS']='30';env['PREVIEW_CUES']='3'
    subprocess.run([sys.executable,'-u',str(work/'render_online.py'),'en-US'],env=env,check=True)
    report=json.loads((work/'voice/audio/en-US/render_report.json').read_text())
    assert report['audio_seconds']==30 and report['mp3_decoded_duration']['verified']
    assert report['narration_style_id']=='science-documentary-expressive-v1'
    assert report['prosody_summary']['word_boundaries']>0 and report['prosody_summary']['word_accents']>0
    print('Expressive30-second preview passed word-boundary and duration checks')
elif locale=='mww':
    folder=work/'voice/audio/mww';folder.mkdir(parents=True,exist_ok=True)
    for p in Path('input/native-hmong').iterdir():shutil.copy(p,folder/p.name)
    report=json.loads((folder/'render_report.json').read_text());audio=folder/report['mp3_file']
    assert hashlib.sha256(audio.read_bytes()).hexdigest()==report['mp3_sha256']
    sys.path.insert(0,str(tool));from timing import measure_encoded
    result=measure_encoded(audio,folder,48000,57600000);assert result['verified']
    print('Hmong native output verified at 1200 seconds')
else:
    subprocess.run([sys.executable,'-u',str(work/'render_online.py'),locale],env=env,check=True)
    p=work/'voice/audio'/locale/'render_report.json';assert p.exists(),locale
    j=json.loads(p.read_text());assert j['duration_verified'] and j['audio_seconds']==1200
    print('Voice verified:',locale,j['voice_id'])
