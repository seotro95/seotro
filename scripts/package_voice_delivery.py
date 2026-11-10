"""Package verified voices with country names; do not synthesize or alter audio.

Run from a prepared build containing input/delivery_config.json, the original
audio manifest and the shared VOICE_FILE_NAMING.json. Public audio is verified
by original SHA256 before any renamed copy is published. Requires gh only for
publishing; standard-library Python handles packaging.
"""
import concurrent.futures,csv,hashlib,json,os,shutil,subprocess,time,urllib.request,zipfile
from pathlib import Path
C=json.loads(Path('input/delivery_config.json').read_text())
REPO=C['repository'];TAG=C['release_tag'];PREFIX=C['topic_prefix'];OUT=Path('delivery-country');OUT.mkdir(exist_ok=True)
BASE=f'https://github.com/{REPO}/releases/download/{TAG}/'
original=json.loads(Path('input/original_audio_manifest.json').read_text())
naming=json.loads(Path('input/VOICE_FILE_NAMING.json').read_text());names={x['locale']:x for x in naming['voices']}
assert len(original['voices'])==17 and len(names)==17
def fetch(url):
 req=urllib.request.Request(url+('?verify='+str(int(time.time()))),headers={'User-Agent':'CountryVoiceDelivery/1'})
 return urllib.request.urlopen(req,timeout=120).read()
data=fetch(BASE+C['original_details_zip']);assert hashlib.sha256(data).hexdigest()==C['original_details_sha256']
details=OUT/'original-details.zip';details.write_bytes(data)
with zipfile.ZipFile(details) as z:
 for p in z.namelist():assert not Path(p).is_absolute() and '..' not in Path(p).parts
 z.extractall(OUT)
details.unlink()
def copy_voice(row):
 data=fetch(BASE+row['filename']);assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
 n=names[row['locale']];filename=f"{PREFIX}_{n['delivery_slug']}.mp3";assert filename.isascii()
 (OUT/filename).write_bytes(data)
 return dict(row,legacy_filename=row['filename'],filename=filename,name=n['display_name'],country_vi=n['country_vi'],language_vi=n['language_vi'])
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:voices=list(pool.map(copy_voice,original['voices']))
assert len({v['filename'] for v in voices})==17 and len({v['sha256'] for v in voices})==17
manifest=dict(original,voices=voices,filename_naming_profile=naming['naming_profile_id'],audio_content_unchanged=True)
(OUT/'AUDIO_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
profiles=json.loads((OUT/'VOICE_PROFILES_LOCKED.json').read_text());by_locale={v['locale']:v for v in voices}
for p in profiles['profiles']:
 v=by_locale[p['locale']];p.update(delivery_filename=v['filename'],legacy_filename=v['legacy_filename'],country_vi=v['country_vi'],language_vi=v['language_vi'],name=v['name'])
 report_path=OUT/'REPORTS'/f"{p['locale']}.json";r=json.loads(report_path.read_text())
 assert r['mp3_sha256']==v['sha256'] and r['voice_id']==v['voice_id'] and r['audio_seconds']==C['target_seconds']
 r.update(previous_mp3_file=v['legacy_filename'],mp3_file=v['filename'],delivery_naming_profile=naming['naming_profile_id'],audio_unchanged_by_renaming=True)
 report_path.write_text(json.dumps(r,ensure_ascii=False,indent=2))
profiles['filename_naming_profile']=naming['naming_profile_id']
(OUT/'VOICE_PROFILES_LOCKED.json').write_text(json.dumps(profiles,ensure_ascii=False,indent=2))
(OUT/'VOICE_FILE_NAMING.json').write_text(json.dumps(naming,ensure_ascii=False,indent=2))
with (OUT/'TEN_VOICE_THEO_QUOC_GIA.csv').open('w',newline='') as f:
 fields=['name','country_vi','language_vi','gender','filename','legacy_filename','locale','voice_id','seconds','sha256'];w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(voices)
readme=f"# {C['topic_name']} — 17 voice đặt tên theo quốc gia\n\nMỗi bản dài **20:00**, có nhấn nhá và giữ đúng mã giọng cũ: 16 nam, H’Mông nữ. Video chính chỉ dùng tiếng Anh.\n\n"
readme+=f"[Tải ZIP đủ 17 giọng theo tên quốc gia]({BASE}{C['country_audio_zip']}) · [Hồ sơ giọng, lời và thời gian]({BASE}{C['country_details_zip']})\n\n"
readme+='| Quốc gia / ngôn ngữ | Giọng | Tệp MP3 |\n|---|---|---|\n'
for v in voices:readme+=f"| {v['name']} | {'Nữ' if v['gender']=='Female' else 'Nam'} | [{v['filename']}]({BASE}{v['filename']}) |\n"
readme+='\nTên tệp dùng tiếng Việt không dấu để dễ tải và dùng trên Windows. Mỹ là bản tiếng Anh của giọng US đã chọn. H’Mông được ghi theo ngôn ngữ, không gán thành một quốc gia.\n\n'
readme+='Audio được giữ nguyên từng byte so với bản đã kiểm tra: mỗi tệp giải mã đúng 1.200 giây, tương ứng 57.600.000 mẫu ở 48 kHz. Tiếng Anh căn 120 đoạn 10 giây; bản dịch căn 12 chương 100 giây, không phải căn từng từ giữa các ngôn ngữ. Giữ science-prehistory-17-v1 và science-documentary-expressive-v1.\n\n'
readme+='Hồ sơ vẫn lưu locale và mã giọng để các tập sau khớp giọng cũ. Các tệp tên mã trước đây được giữ để đường dẫn đã gửi vẫn hoạt động. Bản dịch và phương ngữ H’Mông Trắng vẫn cần người bản ngữ nghe/đọc rà soát.\n'
(OUT/'README.md').write_text(readme)
files=[p for p in sorted(OUT.rglob('*')) if p.is_file() and p.suffix!='.zip']
with zipfile.ZipFile(OUT/C['country_audio_zip'],'w',compression=zipfile.ZIP_STORED) as z:
 for p in files:z.write(p,p.relative_to(OUT))
with zipfile.ZipFile(OUT/C['country_details_zip'],'w',compression=zipfile.ZIP_DEFLATED) as z:
 for p in files:
  if p.suffix!='.mp3':z.write(p,p.relative_to(OUT))
with zipfile.ZipFile(OUT/C['country_audio_zip']) as z:
 assert len([n for n in z.namelist() if n.endswith('.mp3')])==17
 for v in voices:assert hashlib.sha256(z.read(v['filename'])).hexdigest()==v['sha256']
assets=[v['filename'] for v in voices]+[C['country_audio_zip'],C['country_details_zip'],'AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_FILE_NAMING.json','TEN_VOICE_THEO_QUOC_GIA.csv','README.md']
for name in assets:subprocess.run(['gh','release','upload',TAG,str(OUT/name),'--repo',REPO,'--clobber'],check=True)
notes=f"{C['topic_name']}, chủ đề 3: kịch bản tiếng Anh 20 phút, 100 prompt trong 10 TXT, 20 vị trí dùng lại cảnh.\n\n"+readme
notes+=f"\n[Tải tài liệu kịch bản và prompt]({BASE}MALTA_VIDEO_03_TAI_LIEU_20_PHUT.zip)\n"
(OUT/'RELEASE_NOTES.md').write_text(notes)
subprocess.run(['gh','release','edit',TAG,'--repo',REPO,'--notes-file',str(OUT/'RELEASE_NOTES.md')],check=True)
receipt=dict(voice_count=17,audio_content_unchanged=True,assets=[dict(name=n,bytes=(OUT/n).stat().st_size,sha256=hashlib.sha256((OUT/n).read_bytes()).hexdigest()) for n in assets])
(OUT/'COUNTRY_DELIVERY_QA.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
subprocess.run(['gh','release','upload',TAG,str(OUT/'COUNTRY_DELIVERY_QA.json'),'--repo',REPO,'--clobber'],check=True)
print('Published all17 country-named voices; original audio hashes unchanged.',flush=True)
