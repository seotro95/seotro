from pathlib import Path
import hashlib,json,os,subprocess,zipfile
P=Path(__file__).resolve().parent
ready=json.loads((P/'VOICE_EXPORT_READY.json').read_text())
assert ready['topic']==42 and ready['target_seconds']==1242
assert ready['export_scope']=='17 completed MP3 voices and saved voice profiles only'
repo=os.environ['GITHUB_REPOSITORY'];tag='cooking-video-42-20m42s'
def api_release():
 return json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/releases/tags/{tag}'],text=True))
before=api_release();doc=next(a for a in before['assets'] if a['name']=='COOKING_42_TAI_LIEU_20m42s.zip')
manifest=json.loads((P/'AUDIO_MANIFEST.json').read_text());assert len(manifest)==17 and len({m['sha256'] for m in manifest})==17
profiles={p['locale']:p for p in json.loads((P/'VOICE_PROFILES_LOCKED.json').read_text())['profiles']}
assert len(profiles)==17 and sum(p['gender'].casefold()=='male' for p in profiles.values())==16
assets=[]
for m in manifest:
 f=P/m['filename'];assert f.parent==P and f.suffix=='.mp3'
 assert f.stat().st_size==m['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==m['sha256']
 assert m['decoded_seconds']==1242 and m['decoded_samples_48000']==59616000
 assert m['voice_id']==profiles[m['locale']]['voice_id'];assets.append(f)
for name in ['VOICE_PROFILES_LOCKED.json','NARRATION_STYLE_LOCKED.json','NARRATION_DELIVERY_PROFILE.json','VOICE_FILE_NAMING.json']:
 f=P/name;record=ready['profile_files'][name];assert hashlib.sha256(f.read_bytes()).hexdigest()==record['sha256'];assets.append(f)
assets.append(P/'AUDIO_MANIFEST.json')
archive=P/'COOKING_42_17_VOICES_20m42s.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_STORED) as z:
 for m in manifest:z.write(P/m['filename'],m['filename'])
with zipfile.ZipFile(archive) as z:assert len(z.namelist())==17 and z.testzip() is None
assets.append(archive)
qa={'topic':42,'voice_count':17,'duration_seconds_each':1242,'decoded_samples_each_48000':59616000,'uploaded_audio_matches_verified_local_files':True,'tts_generation_executed_in_export':False,'export_commit':os.environ['GITHUB_SHA'],'export_scope':ready['export_scope'],'voice_zip_bytes':archive.stat().st_size,'voice_zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'existing_document_zip_digest':doc.get('digest'),'existing_document_zip_asset_id':doc['id'],'document_archive_rebuilt_or_uploaded':False,'independent_native_review':False}
(P/'VOICE_PUBLICATION_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2));assets.append(P/'VOICE_PUBLICATION_QA.json')
checksums=P/'VOICE_SHA256SUMS.txt';checksums.write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in assets));assets.append(checksums)
assert all(f.suffix=='.mp3' or f.name in {'VOICE_PROFILES_LOCKED.json','NARRATION_STYLE_LOCKED.json','NARRATION_DELIVERY_PROFILE.json','VOICE_FILE_NAMING.json','AUDIO_MANIFEST.json','COOKING_42_17_VOICES_20m42s.zip','VOICE_PUBLICATION_QA.json','VOICE_SHA256SUMS.txt'} for f in assets)
for f in assets:
 subprocess.run(['gh','release','upload',tag,str(f),'--repo',repo,'--clobber'],check=True);print('Uploaded voice/profile asset:',f.name,flush=True)
after=api_release();doc_after=next(a for a in after['assets'] if a['name']==doc['name'])
assert doc_after['id']==doc['id'] and doc_after.get('digest')==doc.get('digest') and doc_after['size']==doc['size']
base=f'https://github.com/{repo}/releases/download/{tag}/'
body=before.get('body','').replace('Voice đang được tạo và kiểm tra; chưa công bố link MP3 chưa tồn tại.','Đã hoàn tất 17 voice, mỗi bản đúng 20:42. Giữ 16 giọng nam và H’mông Trắng nữ female-3.')
body+='\n\n[Tải ZIP đủ 17 voice]('+base+archive.name+')\n\n| Quốc gia/ngôn ngữ | Tải riêng |\n|---|---|\n'
names=json.loads((P/'VOICE_FILE_NAMING.json').read_text())['voices']
for v in names:body+='| '+v['display_name']+' | [MP3]('+base+'COOKING_42_'+v['delivery_slug']+'.mp3) |\n'
body+='\nCác MP3 đã đối chiếu mã hash và giải mã đúng 59.616.000 mẫu ở 48 kHz. Bộ tài liệu giữ bản đã công bố; gói cập nhật báo cáo và bản dịch chưa được công bố. Nghe duyệt độc lập bởi người bản ngữ và kiểm tra phương ngữ H’mông vẫn cần thực hiện.\n'
notes=P/'VOICE_RELEASE_NOTES.md';notes.write_text(body)
subprocess.run(['gh','release','edit',tag,'--repo',repo,'--notes-file',str(notes),'--latest=false'],check=True)
print('Published only17voices and saved profiles; existing document ZIP preserved byte-for-byte',flush=True)
