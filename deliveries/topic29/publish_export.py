from pathlib import Path
import hashlib,json,os,re,subprocess,zipfile
P=Path(__file__).resolve().parent;ready=json.loads((P/'EXPORT_READY.json').read_text());repo=os.environ['GITHUB_REPOSITORY'];tag=ready['release_tag']
assert ready['topic']==29 and ready['target_seconds']==1302 and ready['expected_samples_48000']==62496000 and ready['export_only_no_voice_generation'] is True
for record in ready.get('transport',[]):
 assert re.fullmatch(r'[A-Za-z0-9_.-]+',record['name'])
 with (P/record['name']).open('wb') as output:
  for part in record['parts']:
   assert part['path'].startswith('transport/') and '..' not in part['path']
   data=(P/part['path']).read_bytes();assert len(data)==part['bytes'] and hashlib.sha256(data).hexdigest()==part['sha256'];output.write(data)
for asset in ready['assets']:
 assert re.fullmatch(r'[A-Za-z0-9_.-]+',asset['name'])
 file=P/asset['name'];assert file.stat().st_size==asset['bytes'] and hashlib.sha256(file.read_bytes()).hexdigest()==asset['sha256'],asset['name']
manifest=json.loads((P/'AUDIO_MANIFEST.json').read_text());assert len(manifest)==17 and len({m['sha256'] for m in manifest})==17
for item in manifest:
 assert item['decoded_seconds']==1302 and item['decoded_samples_48000']==62496000
 assert hashlib.sha256((P/item['filename']).read_bytes()).hexdigest()==item['sha256']
archive=P/'CALCULUS_29_17_VOICES_21m42s.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_STORED) as z:
 for item in manifest:z.write(P/item['filename'],item['filename'])
with zipfile.ZipFile(archive) as z:assert len(z.namelist())==17 and z.testzip() is None
qa={'topic':29,'voice_count':17,'duration_seconds_each':1302,'decoded_samples_each_48000':62496000,'uploaded_audio_matches_verified_local_files':True,'tts_generation_executed_in_export':False,'export_commit':os.environ['GITHUB_SHA'],'voice_zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'voice_zip_bytes':archive.stat().st_size,'independent_native_language_review':False}
(P/'PUBLICATION_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
assets=[P/a['name'] for a in ready['assets']]+[archive,P/'PUBLICATION_QA.json']
checksums=P/'SHA256SUMS.txt';checksums.write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in assets));assets.append(checksums)
subprocess.run(['gh','release','view',tag,'--repo',repo],check=True)
for file in assets:
 subprocess.run(['gh','release','upload',tag,str(file),'--repo',repo,'--clobber'],check=True)
 print('Uploaded',file.name,flush=True)
subprocess.run(['gh','release','edit',tag,'--repo',repo,'--title','Cao răng cổ — chủ đề29 — 17 voice 21:42 và 130 prompt','--notes-file',str(P/'README.md'),'--draft=false','--latest=false'],check=True)
print('Completed voice export without regenerating any voice',flush=True)
