import csv,hashlib,json,re,shutil,urllib.request,zipfile
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';P=D/'PROMPTS';S=R/'voice/scripts'
for p in [D,P,S]:p.mkdir(parents=True,exist_ok=True)
C=json.loads((R/'EPISODE.json').read_text());T=C['target_seconds'];PREFIX=C['prefix'];BASE=f"https://github.com/seotro95/seotro/releases/download/{C['release_tag']}/"
def dump(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def stamp(t):return f'{t//3600:02}:{t%3600//60:02}:{t%60:02},000'
raw=[x.split('\t') for x in (R/'CUES_MASTER.tsv').read_text().splitlines()];assert len(raw)==200 and all(len(x)==8 for x in raw)
rows=[dict(id=int(i),section=int(sec),start=int(a),end=int(b),kind=k,voice=v,visual=vis,mode=mode) for i,sec,a,b,k,v,vis,mode in raw]
assert rows[0]['start']==0 and rows[-1]['end']==T and all(a['end']==b['start'] for a,b in zip(rows,rows[1:]))
assert all(3<=x['end']-x['start']<=10 and not re.search(r'\d',x['voice']) for x in rows)
voice=[{k:x[k] for k in ['id','start','end','voice']} for x in rows]
dump(S/'en-US.json',voice);dump(D/'ENGLISH_CUES_200.json',voice);dump(D/'CUES_WITH_SCENES.json',rows)
hooks=[x['start'] for x in rows if x['kind']=='rehook'];caveats=[x for x in rows if x['kind']=='caveat'];gaps=[b-a for a,b in zip(hooks,hooks[1:])];cg=[b['start']-a['start'] for a,b in zip(caveats,caveats[1:])]
assert min(gaps)>=60 and max(gaps)<=90 and min(cg)>=120 and len(caveats)==10
assert rows[0]['end']==10 and rows[2]['end']<30 and rows[4]['start']<120
assert all(any(x['kind']=='scene' for x in rows if x['section']==i) for i in range(1,11))
assert rows[-1]['voice']=="What lies beneath the Eye's oldest rings?"
ret=dict(status='passed',version='retention-v5',hook_object='one tilted sedimentary layer',first_shot_seconds=10,promise_cue_id=3,promise_completed_seconds=rows[2]['end'],first_payoff_cue_id=5,first_payoff_start_seconds=rows[4]['start'],rehook_starts=hooks,rehook_gaps_seconds=gaps,max_rehook_gap=max(gaps),caveat_cue_ids=[x['id'] for x in caveats],caveat_start_gaps_seconds=cg,min_caveat_gap=min(cg),caveats_per_section=1,caveat_beat_seconds=[x['end']-x['start'] for x in caveats],sections=10,each_section_has_present_tense_scene=True,section_endings_are_turn_or_question=True,voice_cue_duration_values=sorted({x['end']-x['start'] for x in rows}),all_english_numbers_spelled_out=True,final_single_mystery=rows[-1]['voice'],review_method='Deterministic timing/annotation checks plus assistant editorial review; no automatic claim of human viewer retention measured')
dump(D/'RETENTION_QA.json',ret);dump(D/'RETENTION_RULES_LOCKED.json',dict(version='retention-v5',first_ten_seconds_one_object=True,promise_before_seconds=30,first_payoff_before_seconds=120,rehook_every_seconds=[60,90],minimum_gap_caveat_beats_seconds=120,voice_blocks_seconds=[3,10],present_tense_scene_each_section=True,each_section_ends_on_turn=True,english_numbers_as_words=True,ending_answers_then_one_mystery=True,no_auto_start_next_topic=True))
chapters=[]
for i in range(1,11):
 g=[x for x in rows if x['section']==i];chapters.append(dict(id=i,start=g[0]['start'],end=g[-1]['end'],source_cue_ids=[x['id'] for x in g],voice=' '.join(x['voice'] for x in g)))
assert [x['end']-x['start'] for x in chapters]==C['section_seconds'];dump(D/'SECTIONS_10_FULL_EN.json',chapters)
asset=json.loads((R/'SOURCE_ASSET_MANIFEST.json').read_text());A=R/'REFERENCE_ASSETS';A.mkdir(exist_ok=True);img=A/asset['filename']
if not img.exists():
 with urllib.request.urlopen(asset['url'],timeout=90) as res,img.open('wb') as f:shutil.copyfileobj(res,f)
assert img.stat().st_size==asset['bytes'] and sha(img)==asset['sha256']
(D/'REFERENCE_ASSETS').mkdir(exist_ok=True);shutil.copyfile(img,D/'REFERENCE_ASSETS'/img.name);dump(D/'REFERENCE_ASSETS'/'SOURCE_ASSET_MANIFEST.json',asset)
(D/'REFERENCE_ASSETS'/'CREDIT_AND_FRAMING.txt').write_text(asset['credit']+'\n'+asset['source_page']+'\n'+asset['policy']+'\n'+asset['clip_framing']+'\nNo endorsement implied. Source JPEG unchanged.\n')
opening=[
('This same tan sedimentary bed rises at a gentle angle and curves out of view; three natural darker bedding stripes identify the illustrative opening outcrop. One concrete object only, no cutaway or orbital insert.','field',0,10),
('Ground-level reveal from the opening bed to two additional low curved rocky ridges beyond, ordinary arid plateau scale.','field',10,14),
('Registered crop of the provided real Landsat reference along an inner rocky arc; original geometry and textures remain fixed.','satellite',14,18),
('Widen digital framing on the provided reference to show the complete slightly elliptical Richat formation, plateau and dunes.','satellite',18,22),
('Mature adult observer beside the same naturally tilted bed, only the adult hand and the continuous solid rock edge in view.','field',22,26),
('Close alternating resistant sandstone ledges and lower softer bands in an illustrative open outcrop, the first concrete erosion clue.','macro',26,30)]
shots=[dict(id=i+1,start=a,end=b,visual=v,mode=m,kind='opening',used=True) for i,(v,m,a,b) in enumerate(opening)]
for start in range(30,1300,10):
 end=start+10;mid=(start+end)/2;key=next(x for x in rows if x['start']<=mid<x['end']);shots.append(dict(id=len(shots)+1,start=start,end=end,visual=key['visual'],mode=key['mode'],kind='main',used=True))
shots.append(dict(id=len(shots)+1,start=1300,end=1302,visual=rows[-1]['visual'],mode=rows[-1]['mode'],kind='ending',used=True))
assert len(shots)==134 and sum(x['end']-x['start'] for x in shots)==T
backup=[('Same opening tilted tan bed under side light, continuous darker bedding stripes visible without any damage.','field'),('Low dry channel cutting an arid plateau, solid ridges beyond and natural wind motion in loose sand.','field'),('Outdoor layered dome model with its removed upper cover resting separately beside the truncated base.','model'),('Macro stable breccia replica with distinct fragments and pale cavity fill, no claimed recovered specimen.','macro'),('Registered framing on the real reference at the margin between outer rocky arcs and dune fields, no invented rings.','satellite'),('Dark coarse-crystalline rock replica beside a separate pale sedimentary sample on an outdoor support.','macro')]
for v,m in backup:shots.append(dict(id=len(shots)+1,start=None,end=None,visual=v,mode=m,kind='backup_not_on_timeline',used=False))
silent='Video không có âm thanh, không có lời nói.'
cameras={
'field':['Low 35 mm side track along the bed, stable horizon and restrained natural parallax.','Wide 24 mm slow lateral reveal of the landform, keep real-world scale and shallow relief.','Medium 50 mm measured forward push toward the rock contact, no handheld shake.','Long 85 mm gentle lateral move showing separate ridge depths, no impossible whole-site view from the ground.'],
'macro':['Macro 100 mm shallow but readable focus pull across grains, fixed material identity.','Close 85 mm oblique side slide along the boundary between materials, no morphing.','Macro 90 mm slow arc with raking daylight, stable crystal and fragment scale.'],
'model':['High oblique 50 mm slow arc around the fixed outdoor physical teaching model.','Low 65 mm lateral track along the open model section, keep pieces physically connected.','Overhead 50 mm measured diagonal move revealing the relation between separate model stages.'],
'deep_time':['Slow 35 mm lateral move across a clearly illustrative outdoor deep-time geological reconstruction.','High oblique 50 mm steady drift over a separate explanatory crustal model, stable geometry.'],
'satellite':['Nadir registered digital pan across the supplied two-dimensional Landsat image; no simulated ground relief.','Slow orthographic zoom outward within the original reference image, preserving every ring and ridge.','Restrained registered diagonal pan on the provided real mosaic, no perspective warping.']}
for x in shots:
 overlap=[v for v in rows if x['used'] and v['start']<x['end'] and v['end']>x['start']]
 x.update(generation_seconds=10,use_seconds=x['end']-x['start'] if x['used'] else 0,source_filename=f'RICHAT_{x["id"]:03}.mp4',voice_cue_ids=[v['id'] for v in overlap],voice=' '.join(v['voice'] for v in overlap),section_ids=sorted({v['section'] for v in overlap}),setting='outdoor',camera=cameras[x['mode']][(x['id']-1)%len(cameras[x['mode']])])
 ref=('Use the supplied unchanged NASA/USGS reference REFERENCE_ASSETS/richat_landsat_2026.jpg. Animate framing over the actual image, not invented satellite pixels; preserve the slightly elliptical irregular Richat rings, surrounding plateau, channels and dune geometry. Keep the video crop clear of the original bottom-left compass and scale legend; no new labels, borders, numbers or logos. This is a motion treatment of a real two-dimensional mosaic, not actual aerial footage, a DEM or ground motion. ' if x['mode']=='satellite' else '')
 x['prompt']=('One continuous 10-second shot, landscape 16:9, cinematic outdoor geological documentary, natural desert light and restrained camera movement. '+x['visual']+' Camera: '+x['camera']+' '+ref+
 'Field outcrops and sample close-ups are plausible illustrative reconstructions or comparison replicas, never authenticated Richat field footage, recovered artifacts, dated samples or measured data. Geological models are visibly separate explanatory teaching models, simplified and not to scale; do not copy published diagrams or invent analytical graphs. '
 'Richat is a low, deeply eroded geological structure in Mauritania, not a perfect circular wall, city, stepped pyramid, alien base, confirmed impact crater, active modern volcano or immense unbroken mountain rim. Sedimentary beds follow plausible gentle outward dips. Keep parallel sill sheets distinct from crosscutting dykes. Show carbonatite as igneous carbonate-rich material when specified, not an ordinary limestone building block. '
 'Deep-time scenes are explanatory reconstructions with no people, buildings, modern equipment, dinosaurs or decorative animals. Buried magma and fluid routes are hypotheses shown as models, not directly observed chambers, exact subterranean geometry or current surface eruptions. No instantaneous real-landscape uplift, magical erosion, morphing rock types, dramatic disaster montage, explosions or glowing crystals. '
 'No laboratory, white coats, indoor scientist scene, operating microscope, classroom wall or clinical room. Prioritize open desert, geological field context, outdoor physical models and the supplied real satellite reference. '
 'No children, infants, adolescents, minors, child portraits, minors in backgrounds, screens, shadows or reflections. All visible people and hands must be clearly adult age 35–65, modern anonymous field observers. No damaging, hammering or collecting from the protected formation. '
 'No lip-sync, readable text, letters, dates, labels, captions, signs, branding, logos or watermark. Stable anatomy, terrain, object scale and material identity throughout. '+silent)
assert len(shots)==140 and len({x['prompt'] for x in shots})==140
for i in range(0,140,10):(P/f'PROMPT_{i//10+1:02}_{i+1:03}-{i+10:03}.txt').write_text('\n\n'.join(f"{x['id']:03}. {x['prompt']}" for x in shots[i:i+10])+'\n')
dump(D/'ALL_PROMPTS.json',shots);dump(D/'OPENING_6_SHOTS_30s.json',shots[:6]);dump(D/'BACKUP_135_140.json',shots[134:])
fields=['id','start','end','use_seconds','generation_seconds','voice_cue_ids','voice','source_filename','kind','mode','setting','visual','camera','prompt']
for name,subset in [('TIMELINE_134_CANH.csv',shots[:134]),('PROMPT_INDEX_140.csv',shots)]:
 with (D/name).open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(subset)
(D/'KICH_BAN_EN_21m42s.txt').write_text('\n\n'.join(x['voice'] for x in rows)+'\n')
(D/'KICH_BAN_EN_CO_MOC.txt').write_text('\n\n'.join(f"{x['id']:03} | {stamp(x['start'])} → {stamp(x['end'])} | PHẦN {x['section']} | {x['kind']}\n{x['voice']}" for x in rows)+'\n')
(D/'en-US.srt').write_text('\n\n'.join(f"{x['id']}\n{stamp(x['start'])} --> {stamp(x['end'])}\n{x['voice']}" for x in rows)+'\n')
for n in ['EPISODE.json','SOURCE_ASSET_MANIFEST.json','NGUON_KIEM_CHUNG.md','PHAN_TICH_VA_KE_HOACH_DUNG.md','PRODUCTION_STEPS_APPLIED.md','5_TIEU_DE_VA_THUMBNAIL.txt','VOICE_PROFILES_LOCKED_BASELINE.json','MELO_SOURCE_LOCK.json']:shutil.copyfile(R/n,D/n)
words=sum(len(re.findall(r"\b[\w'-]+\b",x['voice'])) for x in rows)
qa=dict(status='passed',topic_id=C['topic_id'],catalogue_id='new-100-topics-20261116',target_seconds=T,english_words=words,english_wpm=round(words/(T/60),3),english_cues=len(rows),voice_cue_duration_values=ret['voice_cue_duration_values'],unique_prompts=140,prompt_txt_files=14,prompts_per_txt=10,timeline_shots=134,backup_prompt_ids=C['backup_ids'],timeline_total_seconds=T,opening_shots=6,opening_seconds=30,first_shot_seconds=10,all_prompts_silent_suffix=True,all_prompts_exclude_minors=True,translated_sections=10,section_seconds=C['section_seconds'],expected_audio_frames_48000=C['frames'],requested_voice_count=16,all_requested_voices_male=True,vietnamese_voice_id='vi-VN-NamMinhNeural',voices_generated=False,footage_generated=False,video_edited=False,visual_revision='richat-outdoor-reference-v5',outdoor_scenes=140,laboratory_scenes=0,reference_image_sha256=asset['sha256'],reference_image_credit=asset['credit'],retention_qa_status='passed')
dump(D/'DOCUMENT_QA.json',qa)
(D/'HUONG_DAN_SU_DUNG.txt').write_text(f'''MỚI-061 — MẮT SAHARA / RICHAT — 21:42

Kịch bản Anh {words} từ, khoảng {words/(T/60):.1f} từ/phút. 200 block lời3–10giây, không buộc mỗi block bằng một clip10s. 10phần chung:9×130+132giây. Hook đầu giữ một lớp đá10s, promise<30s, payoff<2phút, rehook60–90s, một beat caveat cuối mỗi phần cách≥120s, kết bằng một câu hỏi còn mở. Xem RETENTION_QA.json.
140prompt/14TXT×10. Timeline134cảnh:clip001 dùng10s;002–006 dùng4s/cảnh;007–133 dùng10s/cảnh;134 dùng2s. 135–140 là6dự phòng, không cộng thời lượng. CSV gắn các ID lời chồng lấn. Mỗi prompt tạo10s, kết “{silent}”. Khi dựng xóa âm clip và chỉ dùng voiceAnh, không nhạc/SFX. Cảnh thiếu thay video chuyển động liên quan, không ảnh đứng có chữ.
Không trẻ em, lab/áo blouse, chữ đọc được. Toàn cảnh Richat bám ảnh NASA/USGS kèm theo; crop khung video tránh chú giải dưới trái, giữ địa hình, ghi credit khi xuất bản. ẢnhJPEG gốc không chỉnh sửa; cảnh field/model/deep-time chỉ minh họa, không footage hoặc dữ liệu đo thật. Không thành phố, người ngoài hành tinh, hố va chạm xác định hoặc magma đang phun ở Richat hiện đại. Các mô hình ngầm/tuổi phải giữ mức chắc chắn trong lời.
Giữ16IDnam, gồm Andrew/NamMinh. Backendonline khóa củaMelo-Viet-Studio1.3.1 / MicrosoftEdge quaedge-tts; khôngUIWindows hoặcmodelMelo đa ngôn ngữ cục bộ. Không đổi pitch, không cắt từ để ép thời lượng, không lấp im lặng dài. MỗiMP3 phải giải mã62.496.000mẫu mono48kHz=1.302s. Anh căn200block; bản nước ngoài chuyển thể10phần, không dịch từng câu hoặc khớp từng từ. SRTdịch theo phần cần chia nhỏ trước khi hiển thị. Chưa kiểm nghe/biên tập bản ngữ độc lập.
Chưa tạo footage mới, ảnhthumbnail hoặcMP4hoàn chỉnh.\n''')
(D/'README.md').write_text(f'''# MỚI-061 — Mắt Sahara / Richat — 21:42

[Tài liệu]({BASE}{PREFIX}_TAI_LIEU_21m42s.zip) · [14 TXT prompt]({BASE}{PREFIX}_PROMPT_14_TXT.zip) · [Kịch bản Anh]({BASE}KICH_BAN_EN_21m42s.txt) · [5 tiêu đề/thumbnail]({BASE}5_TIEU_DE_VA_THUMBNAIL.txt)

Kịch bản mới {words} từ, {words/(T/60):.1f} từ/phút, 200block3–10giây. Hook một lớp đá10s; câu hỏi chính trước30s, payoff sớm, rehook60–90s, caveat cách≥120s. Mười phần10×20block; cuối cùng trả lời nguồn gốc địa chất rồi một câu hỏi ngầm. Đọc RETENTION_QA.json, nguồn và kế hoạch dựng.

140prompt/14TXT×10, timeline134cảnh:10+5×4+127×10+2=1.302s;135–140dự phòng. Không trẻ em/lab/chữ/âm thanh/lời nói. Ảnh tham chiếu thậtNASA/USGS cócredit; cảnh dựng chỉ minh họa, không dữ liệu khảo sát hay xác nhận hố thiên thạch/thành phố. Chưa tạo footage mới, thumbnail hoặcMP4.

Giữ16IDgiọng nam, gồm Andrew/NamMinh, qua backendonline khóaMelo-Viet-Studio1.3.1 /MicrosoftEdge. Tài liệu phát hành trước audio; chỉ báo đủ khi đã kiểm giải mã từngMP3đúng1.302s. Bản nước ngoài chuyển thể10phần(9×130+132), không đồng bộ từng từ, chưa kiểm nghe bản ngữ độc lập.
''')
for suffix,root,pattern in [('TAI_LIEU_21m42s',D,None),('PROMPT_14_TXT',P,'*.txt')]:
 with zipfile.ZipFile(R/f'{PREFIX}_{suffix}.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(root.glob(pattern) if pattern else root.rglob('*')):
   if p.is_file():z.write(p,p.relative_to(root))
print(json.dumps(qa,ensure_ascii=False),flush=True)
