from pathlib import Path
import json,hashlib,os,subprocess,zipfile
P=Path(__file__).resolve().parent;ready=json.loads((P/'VOICE_EXPORT_READY.json').read_text());assert ready['topic']==50 and ready['target_seconds']==1272 and ready['expected_samples_48000']==61056000
assert ready['export_scope']=='17 completed MP3 voices, saved voice profiles and audio verification only'
repo=os.environ['GITHUB_REPOSITORY'];tag='mammoth-steppe-video-50-21m12s'
def release():return json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/releases/tags/{tag}'],text=True))
before=release();doc=next(x for x in before['assets'] if x['name']=='MAMMOTH_STEPPE_50_TAI_LIEU_21m12s.zip')
manifest=json.loads((P/'AUDIO_MANIFEST.json').read_text());assert len(manifest)==17 and len({m['sha256'] for m in manifest})==17
profiles={p['locale']:p for p in json.loads((P/'VOICE_PROFILES_LOCKED.json').read_text())['profiles']};assert len(profiles)==17 and sum(p['gender'].casefold()=='male' for p in profiles.values())==16;assert profiles['vi-VN']['voice_id']=='Adam' and profiles['mww']['voice_id']=='hmong-female-3'
assets=[]
for m in manifest:
 f=P/m['filename'];assert f.parent==P and f.suffix=='.mp3';assert f.stat().st_size==m['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==m['sha256'];assert m['decoded_seconds']==1272 and m['decoded_samples_48000']==61056000 and m['voice_id']==profiles[m['locale']]['voice_id'];assets.append(f)
for name,record in ready['profile_files'].items():
 f=P/name;assert f.parent==P and f.suffix=='.json';assert f.stat().st_size==record['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==record['sha256'];assets.append(f)
assets.extend(P/n for n in ['AUDIO_MANIFEST.json','AUDIO_SIGNAL_CHECK.json','PROVIDER_TEXT_METADATA_AUDIT.json'])
archive=P/'MAMMOTH_STEPPE_50_17_VOICES_21m12s.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_STORED) as z:
 for m in manifest:z.write(P/m['filename'],m['filename'])
with zipfile.ZipFile(archive) as z:assert len(z.namelist())==17 and z.testzip() is None
assets.append(archive)
qa={'topic':50,'voice_count':17,'duration_seconds_each':1272,'decoded_samples_each_48000':61056000,'local_audio_hash_verified_before_upload':True,'voice_zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'voice_zip_bytes':archive.stat().st_size,'existing_document_zip_asset_id':doc['id'],'existing_document_zip_digest':doc.get('digest'),'document_zip_rebuilt_or_uploaded':False,'tts_generation_executed_in_export':False,'export_commit':os.environ['GITHUB_SHA'],'independent_native_listening_review':False}
(P/'VOICE_PUBLICATION_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2));assets.append(P/'VOICE_PUBLICATION_QA.json')
(P/'VOICE_SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in assets));assets.append(P/'VOICE_SHA256SUMS.txt')
for f in assets:subprocess.run(['gh','release','upload',tag,str(f),'--repo',repo,'--clobber'],check=True);print('Uploaded',f.name,flush=True)
after=release();check=next(x for x in after['assets'] if x['name']==doc['name']);assert check['id']==doc['id'] and check.get('digest')==doc.get('digest') and check['size']==doc['size']
base=f'https://github.com/{repo}/releases/download/{tag}/';body=before.get('body','');body+='\n\nĐã hoàn tất17voice, mỗi bản đúng21:12.16nam,gồmViệtAdam;H’môngTrắng nữfemale-3.\n\n[TảiZIPđủ17voice]('+base+archive.name+')\n\n| Quốc gia/ngôn ngữ | Giọng | Tải riêng |\n|---|---|---|\n'
for v in json.loads((P/'VOICE_FILE_NAMING.json').read_text())['voices']:body+='| '+v['display_name']+' | '+profiles[v['locale']]['voice_id']+' | [MP3]('+base+'MAMMOTH_STEPPE_50_'+v['delivery_slug']+'.mp3) |\n'
body+='\nCác MP3giải mã61056000mẫu ở48kHz.15giọng online đối chiếu đủ toàn bộ lời đầu vào với metadata dịch vụ;Adam vàH’mông dùng engine cục bộ. Đồng bộ mốc chương/tổng thời lượng không có nghĩa từng câu của mọi ngôn ngữ khớp từngclip10giây. Cần duyệt nghe bản ngữ độc lập, đặc biệt phương ngữH’mông. Hồ sơ giọng và khóa preset/mô hìnhAdam có trong các tệpJSONtải riêng.\n'
notes=P/'VOICE_RELEASE_NOTES.md';notes.write_text(body);subprocess.run(['gh','release','edit',tag,'--repo',repo,'--notes-file',str(notes),'--latest=false'],check=True)
print('Published17voices and saved profiles; documentZIP unchanged',flush=True)
