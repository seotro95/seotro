from pathlib import Path
import hashlib,json,os,subprocess,zipfile

P=Path(__file__).resolve().parent
ready=json.loads((P/'READY.json').read_text())
assert ready['topic']==42 and ready['target_seconds']==1242
assert ready['expected_samples_48000']==59616000
assert ready['export_only_no_voice_generation'] is True
repo=os.environ['GITHUB_REPOSITORY'];tag=ready['release_tag'];D=P/'documents'
inventory=ready['documents_inventory']
for item in inventory:
 assert item['path'].startswith('documents/') and '..' not in item['path']
 file=P/item['path'];assert file.suffix in {'.txt','.md','.csv','.srt','.json'}
 data=file.read_bytes();data.decode('utf-8')
 assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'], item['path']
doczip=P/'COOKING_42_TAI_LIEU_20m42s.zip'
with zipfile.ZipFile(doczip,'w',zipfile.ZIP_DEFLATED) as z:
 for item in inventory:z.write(P/item['path'],str(Path(item['path']).relative_to('documents')))
with zipfile.ZipFile(doczip) as z:assert z.testzip() is None and len(z.namelist())==len(inventory)
assets=[doczip,D/'KICH_BAN_EN_20m42s.txt',D/'5_TIEU_DE_5_PROMPT_THUMBNAIL.txt',D/'VOICE_PROFILES_LOCKED.json',D/'NARRATION_STYLE_LOCKED.json',D/'GIONG_DA_LUU.md',D/'NGUON_KIEM_CHUNG.md',D/'PHAN_TICH_VIDEO_NGUON.md']+sorted((D/'PROMPTS').glob('*.txt'))
qa={'topic':42,'duration_seconds':1242,'document_text_files':len(inventory),'unique_prompts':120,'prompt_txt_count':12,'title_thumbnail_pairs':5,'tts_generation_executed_in_export':False,'contains_source_media_or_models':False,'export_commit':os.environ['GITHUB_SHA'],'independent_native_review':False}
if ready['voices_complete']:
 manifest=json.loads((D/'AUDIO_MANIFEST.json').read_text());assert len(manifest)==17 and len({m['sha256'] for m in manifest})==17
 for m in manifest:
  f=P/m['filename'];assert f.suffix=='.mp3' and f.parent==P
  assert f.stat().st_size==m['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==m['sha256']
  assert m['decoded_seconds']==1242 and m['decoded_samples_48000']==59616000
 archive=P/'COOKING_42_17_VOICES_20m42s.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_STORED) as z:
  for m in manifest:z.write(P/m['filename'],m['filename'])
 with zipfile.ZipFile(archive) as z:assert len(z.namelist())==17 and z.testzip() is None
 assets += [P/m['filename'] for m in manifest]+[archive,D/'AUDIO_MANIFEST.json']
 qa.update(voice_count=17,decoded_samples_each_48000=59616000,uploaded_audio_matches_verified_local_files=True,voice_zip_bytes=archive.stat().st_size,voice_zip_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
(P/'PUBLICATION_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2));assets.append(P/'PUBLICATION_QA.json')
checksums=P/'SHA256SUMS.txt';checksums.write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in assets));assets.append(checksums)
exists=subprocess.run(['gh','release','view',tag,'--repo',repo],capture_output=True)
if exists.returncode:
 subprocess.run(['gh','release','create',tag,'--repo',repo,'--target',os.environ['GITHUB_SHA'],'--title','Con người bắt đầu nấu chín thức ăn khi nào? — chủ đề42 —20:42','--notes-file',str(D/'README.md'),'--latest=false'],check=True)
for f in assets:
 subprocess.run(['gh','release','upload',tag,str(f),'--repo',repo,'--clobber'],check=True)
 print('Uploaded',f.name,flush=True)
subprocess.run(['gh','release','edit',tag,'--repo',repo,'--title','Con người bắt đầu nấu chín thức ăn khi nào? — chủ đề42 —20:42','--notes-file',str(D/'README.md'),'--latest=false'],check=True)
print('Published only requested topic42 deliverables; no voice generation in export',flush=True)
