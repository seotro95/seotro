"""Assemble a usable local production kit, without claiming Muse ran in CI."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,shutil,subprocess,zipfile
from verify_delivery import verify

ROOT=Path(__file__).resolve().parent
DEST=Path('delivery');DEST.mkdir(exist_ok=True)
KIT=DEST/'Siberia_25m36_Production_Kit'
if KIT.exists():shutil.rmtree(KIT)
shutil.copytree(ROOT/'kit',KIT)
shutil.copyfile(ROOT/'PHAN_TICH_VA_QUY_TRINH.md',KIT/'PHAN_TICH_VA_QUY_TRINH.md')
master=json.loads((ROOT/'master_timeline.json').read_text())
shutil.copyfile(ROOT/'master_timeline.json',KIT/'scripts'/'source_master_timeline.json')
presentation_master={**master,'status':'Shared narration target timeline. Actual completed voice outputs are verified in VOICE_TIMING_VERIFICATION.json. Muse visuals and final video are generated separately on the owner Windows computer.',
 'source_snapshot':'source_master_timeline.json','source_snapshot_sha256':hashlib.sha256((ROOT/'master_timeline.json').read_bytes()).hexdigest()}
(KIT/'scripts'/'master_timeline.json').write_text(json.dumps(presentation_master,ensure_ascii=False,indent=2),encoding='utf-8')
curated=json.loads((ROOT/'curated_cues.json').read_text())
(KIT/'scripts'/'VI_script.txt').write_text('\n\n'.join(curated['vi'][str(i)] for i in range(1,60)),encoding='utf-8')
def run(args):return subprocess.run(args,check=True,capture_output=True,text=True).stdout
repo=os.environ['GITHUB_REPOSITORY'];release='siberia-2536-production-v1'
run(['gh','release','download',release,'--repo',repo,'--pattern','en.wav','--pattern','en.mp3','--pattern','en-report.json','--dir',str(KIT/'audio'),'--clobber'])
report=json.loads((KIT/'audio'/'en-report.json').read_text())
assert report['duration_verified'] and report['sync_ok'] and report['duration_report']['error_frames']==0
assert hashlib.sha256((KIT/'audio'/'en.wav').read_bytes()).hexdigest()==report['audio_sha256']
request=ROOT/'package-request.json'
require_all=json.loads(request.read_text()).get('require_all_voices',False) if request.exists() else False
verified=verify(DEST/'verification',required=require_all)
for name in ['VOICE_TIMING_VERIFICATION.json','TAI_CAC_GIONG.md','TAI_CAC_GIONG.html']:
 shutil.copyfile(DEST/'verification'/name,KIT/name)
 shutil.copyfile(DEST/'verification'/name,DEST/name)
for track in verified['tracks']:
 code=track['code']
 for suffix in ['.srt','.txt','-report.json']:
  source=DEST/'verification'/(code+suffix)
  if source.exists():shutil.copyfile(source,KIT/'scripts'/source.name)
paragraphs=[]
def stamp(ms):
 s=ms//1000;m,s=divmod(s,60);return f'{m:02}:{s:02}'
for chapter in master['chapters']:
 paragraphs.append('## '+chapter['title']+' — '+stamp(chapter['start_ms'])+'–'+stamp(chapter['end_ms']))
 paragraphs.extend(c['text'] for c in master['cues'] if c['chapter']==chapter['title'])
 if chapter['sources']:paragraphs.append('Sources:\n\n'+'\n'.join('- '+u for u in chapter['sources']))
(KIT/'scripts'/'EN_KICH_BAN.md').write_text('# '+master['title']+'\n\n'+'\n\n'.join(paragraphs)+'\n',encoding='utf-8')
status={'assembled_utc':datetime.now(timezone.utc).isoformat(),'reference_sha256':'ba8cf7542ee761b6073ab75167001f11bb86e4c60105ed3440c1581fcefb4cf2',
 'english_wav_sha256':report['audio_sha256'],'duration_seconds':1536,'shot_count':227,
 'muse_media_created_in_this_package':False,'finished_video_included':False,
 'verified_voice_languages':verified['verified_languages'],
 'next_step':'Open Muse 1.6.0 on the owner Windows computer, then launch BAT_DAU_VIDEO.cmd.'}
(KIT/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
archive=DEST/'Siberia_25m36_Production_Kit.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for file in KIT.rglob('*'):
  if file.is_file():z.write(file,Path(KIT.name)/file.relative_to(KIT))
for src,name in [(KIT/'PHAN_TICH_VA_QUY_TRINH.md','PHAN_TICH_VA_QUY_TRINH.md'),
 (KIT/'scripts'/'EN_KICH_BAN.md','EN_KICH_BAN.md'),(KIT/'scripts'/'VI_script.txt','VI_script.txt'),
 (KIT/'README_VI.md','HUONG_DAN_TAI_VA_CHAY.md'),(KIT/'SHOT_LIST.csv','SHOT_LIST.csv')]:shutil.copyfile(src,DEST/name)
assets=[archive,*[DEST/n for n in ['PHAN_TICH_VA_QUY_TRINH.md','EN_KICH_BAN.md','VI_script.txt','HUONG_DAN_TAI_VA_CHAY.md','SHOT_LIST.csv','TAI_CAC_GIONG.md','TAI_CAC_GIONG.html','VOICE_TIMING_VERIFICATION.json']]]
run(['gh','release','upload',release,'--repo',repo,*map(str,assets),'--clobber'])
data=json.loads(run(['gh','api','repos/'+repo+'/releases/436895553']))
checks=[]
for asset in data['assets']:
 digest=asset.get('digest') or ''
 if digest.startswith('sha256:') and asset['name']!='SHA256SUMS.txt':checks.append(digest[7:]+'  '+asset['name'])
(DEST/'SHA256SUMS.txt').write_text('\n'.join(sorted(checks,key=lambda x:x.split('  ',1)[1]))+'\n')
run(['gh','release','upload',release,'--repo',repo,str(DEST/'SHA256SUMS.txt'),'--clobber'])
print('Uploaded production kit:',archive.stat().st_size,'bytes; main English WAV verified; no generated Muse media claimed.',flush=True)
