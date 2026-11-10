import hashlib,json,os,shutil,subprocess,urllib.request
from pathlib import Path
repo=os.environ['GITHUB_REPOSITORY'];tag='baishiya-video-08-22m20s';root=Path('available-voices');root.mkdir(exist_ok=True)
profiles={x['locale']:x for x in json.loads(Path('input/BASELINE_VOICE_PROFILES.json').read_text())['profiles']};names={x['locale']:x for x in json.loads(Path('input/VOICE_FILE_NAMING.json').read_text())['voices']};reports={}
for p in Path('artifacts').rglob('render_report.json'):
 j=json.loads(p.read_text());loc=j['locale']
 if loc=='en-US':continue
 assert loc not in reports;reports[loc]=(j,p.parent/j['mp3_file'])
assert len(reports)==15 and 'en-US' not in reports
sha=subprocess.check_output(['gh','api',f'repos/{repo}/git/ref/heads/codex/baishiya-voice-build-20261110','--jq','.object.sha'],text=True).strip();base=f'https://raw.githubusercontent.com/{repo}/{sha}/native-baishiya08/'
for name in ['render_report.json','BAISHIYA_08_mww_female.mp3']:
 with urllib.request.urlopen(base+name,timeout=90) as f:(root/name).write_bytes(f.read())
h=json.loads((root/'render_report.json').read_text());reports['mww']=(h,root/h['mp3_file']);assert len(reports)==16
verified=[]
for loc,(j,audio) in reports.items():
 p=profiles[loc];assert j['audio_seconds']==1340 and j['duration_verified'] and j['mp3_decoded_duration']['verified'] and j['mp3_decoded_duration']['sample_frames']==64320000
 assert j['voice_id']==p['voice_id'] and j['gender']==p['gender'] and j['narration_style_id']=='science-documentary-expressive-v1'
 assert j['voice_identity_preserved'] and not j['pitch_shift_applied'] and hashlib.sha256(audio.read_bytes()).hexdigest()==j['mp3_sha256']
 if loc=='mww':assert j['reference_sha256']==p['reference_sha256']
 filename='BAISHIYA_08_'+names[loc]['delivery_slug']+'.mp3';dst=root/filename;shutil.copy(audio,dst);verified.append(dict(locale=loc,filename=filename,sha256=j['mp3_sha256'],seconds=1340))
assert len({x['sha256'] for x in verified})==16
for x in verified:subprocess.run(['gh','release','upload',tag,str(root/x['filename']),'--repo',repo,'--clobber'],check=True)
print('AVAILABLE_VOICES_VERIFIED',json.dumps(dict(voice_count=16,english_pending=True,voices=verified)),flush=True)
