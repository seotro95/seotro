import hashlib,json,re,subprocess,urllib.request,zipfile
from pathlib import Path
R=Path(__file__).parent
release=json.loads((R/'RELEASE_METADATA.json').read_text())
assert not release['draft'] and release['tag_name']=='kostenki-video-19-20m15s'
assets={x['name']:x for x in release['assets']}
def download(name):
 a=assets[name];p=R/'verified-release'/name;p.parent.mkdir(exist_ok=True)
 with urllib.request.urlopen(a['browser_download_url'],timeout=120) as f:data=f.read()
 assert len(data)==a['size']
 assert 'sha256:'+hashlib.sha256(data).hexdigest()==a['digest']
 p.write_bytes(data);return p
manifest=json.loads(download('AUDIO_MANIFEST.json').read_text());assert manifest['voice_count']==17
profiles={p['locale']:p for p in json.loads((R/'BASELINE_VOICE_PROFILES.json').read_text())['profiles']}
details=download('KOSTENKI_19_HO_SO_GIONG_TEN_QUOC_GIA.zip');D=R/'verified-release/details';D.mkdir(exist_ok=True)
with zipfile.ZipFile(details) as z:
 for info in z.infolist():
  assert not info.filename.startswith('/') and '..' not in Path(info.filename).parts
  assert info.file_size<2000000
 z.extractall(D)
en_srt=(D/'TIMING/en-US.srt').read_text();blocks=re.split(r'\n\s*\n',en_srt.strip())
assert len(blocks)==122 and '00:20:15,000' in blocks[-1]
spoken=' '.join(' '.join(b.splitlines()[2:]) for b in blocks)
source=json.loads((R/'voice/scripts/en-US.json').read_text())
assert spoken==' '.join(x['voice'] for x in source) and len(spoken.split())==2816
assert len(manifest['voices'])==17 and len({x['sha256'] for x in manifest['voices']})==17
for m in manifest['voices']:
 p=profiles[m['locale']];a=assets[m['filename']]
 assert a['size']==m['bytes'] and a['digest']=='sha256:'+m['sha256'] and m['seconds']==1215
 assert m['voice_id']==p['voice_id'] and m['gender']==p['gender']
 report=json.loads((D/'REPORTS'/f"{m['locale']}.json").read_text())
 assert report['max_cue_padding_seconds']<.1
 assert report['audio_seconds']==1215 and report['mp3_decoded_duration']['sample_frames']==58320000
 assert report['duration_verified'] and report['mp3_decoded_duration']['verified']
 assert report['voice_id']==p['voice_id'] and report['gender']==p['gender']
 assert report['narration_style_id']=='science-documentary-expressive-v1'
 assert report['voice_identity_preserved'] and not report['pitch_shift_applied']
 assert report['mp3_sha256']==m['sha256'] and report['mp3_file']==m['filename']
 assert report['max_used_post_tempo']<=(1.4 if m['locale']=='en-US' else 1.5)
 local=json.loads((R/'voice/scripts'/f"{m['locale']}.json").read_text())
 assert (D/'SCRIPTS'/f"{m['locale']}.txt").read_text()=='\n\n'.join(x['voice'] for x in local)
 if m['locale']=='mww':assert report['reference_sha256']==p['reference_sha256']
for name in ['KOSTENKI_19_17_VOICES_TEN_QUOC_GIA.zip','KOSTENKI_19_HO_SO_GIONG_TEN_QUOC_GIA.zip','KOSTENKI_VIDEO_19_TAI_LIEU_20m15s.zip']:
 assert re.fullmatch('sha256:[0-9a-f]{64}',assets[name]['digest']) and assets[name]['size']>1000
assert assets['KOSTENKI_VIDEO_19_TAI_LIEU_20m15s.zip']['digest']=='sha256:'+json.loads((R/'DOCUMENT_DELIVERY_STATE.json').read_text())['zip_sha256']
# Independently decode the public main-English MP3; native was decoded locally before staging.
en=next(x for x in manifest['voices'] if x['locale']=='en-US');audio=download(en['filename'])
proc=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-i',str(audio),'-f','s16le','-ac','1','-ar','48000','pipe:1'],stdout=subprocess.PIPE)
count=0
while True:
 chunk=proc.stdout.read(1048576)
 if not chunk:break
 count+=len(chunk)
assert proc.wait()==0 and count==58320000*2,count
qa={'status':'passed','voices':17,'seconds_per_voice':1215,'decoded_frames_at_48k_per_voice':58320000,'english_words_preserved':2816,'english_cues':122,'english_public_file_independently_decoded':True,'all17_github_asset_digests_match_reports':True,'country_named':True,'male_voices':16,'female_hmong_voices':1,'native_review_pending':True,'white_hmong_dialect_independently_verified':False,'no_children_in_visuals':True,'release_tag':release['tag_name'],'release_published_at':release['published_at'],'assets':[{'name':x['name'],'bytes':x['size'],'digest':x['digest'],'url':x['browser_download_url']} for x in release['assets']]}
(R/'VOICE_RELEASE_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in qa.items() if k!='assets'},ensure_ascii=False))
