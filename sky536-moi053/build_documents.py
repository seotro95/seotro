import csv,json,re,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';P=D/'PROMPTS';S=R/'voice/scripts'
for p in [D,P,S]:p.mkdir(parents=True,exist_ok=True)
TARGET=1332;FRAMES=63936000;PREFIX='SKY536_MOI053';TAG='sky536-moi-053-22m12s';STYLE='sky536-archaeology-outdoors-v1'
BASE=f'https://github.com/seotro95/seotro/releases/download/{TAG}/'
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def stamp(s):return f'{s//3600:02}:{s%3600//60:02}:{s%60:02},000'
raw=[x.split('\t') for x in (R/'CUES_MASTER.tsv').read_text().splitlines()]
assert len(raw)==134 and all(len(x)==4 for x in raw)
rows=[dict(id=int(i),start=(int(i)-1)*10,end=min(int(i)*10,TARGET),voice=v,visual=h,camera=c) for i,v,h,c in raw]
assert [r['id'] for r in rows]==list(range(1,135))
opening=[
('Sixth-century adult farmer looks toward a present but pale sun above grain fields; a stable, inhabited landscape, not global darkness.','Wide low 35 mm push through grain toward the adult silhouette.','outdoor'),
('Clear ice core sleeve on a modern polar field tray, ordinary faint layers, no visible black ash stripe.','Macro 100 mm glide along subtle natural bubbles.','outdoor'),
('Replica timber cross-section in a mountain clearing, natural varied growth rings, no singled-out dated ring.','Macro 85 mm slow arc across the wood surface.','outdoor'),
('Anonymous sixth-century mature writer beneath an open stone portico, manuscript replica marks unreadable.','Close side push toward the hand and pale courtyard light.','outdoor'),
('Unnamed illustrative distant volcanic plume above uninhabited terrain, no identifiable source-volcano claim.','Wide long-lens lateral track with stable grey plume.','outdoor'),
('Clearly artificial outdoor atmosphere model with a fixed translucent upper layer above miniature terrain.','Low side tilt toward the upper layer, no measured data.','outdoor'),
('Sixth-century adults divide grain into a food bowl and a separate seed jar in an open courtyard.','Close overhead move emphasizing the two containers.','outdoor'),
('Living alpine treeline above exposed rocky slopes and a partly sheltered valley, no mass tree death.','Slow wide aerial rise revealing varied elevations.','outdoor'),
('Two unmarked fixed event markers separated along an outdoor physical timeline model, no dates or text.','Macro lateral slide revealing clear space between markers.','outdoor'),
('Unreadable manuscript replica, wood sample and sealed ice sleeve on three separate outdoor supports.','Slow high oblique pullback gathering all three archives in frame.','outdoor')]
shots=[dict(id=i,start=(i-1)*3,end=i*3,kind='opening',visual=v,camera=c,setting=setting,used=True) for i,(v,c,setting) in enumerate(opening,1)]
for r in rows[3:]:
 setting='outdoor'
 shots.append(dict(id=len(shots)+1,start=r['start'],end=r['end'],kind='main',visual=r['visual'],camera=r['camera'],setting=setting,used=True))
assert len(shots)==141 and shots[-1]['end']==TARGET
backup=[('Pale but visible sun over a sixth-century terraced field, mature adult farmer at distance.', 'Wide 50 mm restrained lateral track.', 'outdoor'), ('Replica manuscript fragments on an outdoor stone support, unreadable marks.', 'Macro 100 mm gentle focus pull along worn edges.', 'outdoor'), ('Three different replica growth-ring sections in an alpine field tray.', 'Overhead 65 mm slow diagonal slide.', 'outdoor'), ('Modern adult polar fieldworker closes a protective ice sleeve cradle.', 'Close 50 mm steady side push.', 'outdoor'), ('Unmarked layered atmosphere teaching sculpture outdoors beside a blank relief globe.', 'Wide 35 mm slow arc preserving stable geometry.', 'outdoor'), ('Open-air rural sixth-century seed store with adult workers and partly filled grain bins.', 'Medium 50 mm move past the door into the open courtyard.', 'outdoor'), ('Arctic sea-ice edge with open water, natural surface movement, no instant ice growth.', 'Wide 35 mm low aerial lateral glide.', 'outdoor'), ('Late-antique rural building foundation in an outdoor excavation, adult survey team beyond.', 'High 35 mm diagonal descent toward soil context.', 'outdoor'), ('Same rural horizon as opening beneath clear daylight, standing grain and no people.', 'Fixed wide 50 mm composition with natural wind motion.', 'outdoor')]
for v,c,setting in backup:shots.append(dict(id=len(shots)+1,start=None,end=None,kind='backup_not_on_timeline',visual=v,camera=c,setting=setting,used=False))
silent='Video không có âm thanh, không có lời nói.'
for s in shots:
 overlap=[r for r in rows if s['used'] and r['start']<s['end'] and r['end']>s['start']]
 s.update(generation_seconds=10,use_seconds=s['end']-s['start'] if s['used'] else 0,source_filename=f'SKY536_{s["id"]:03}.mp4',voice_cue_ids=[r['id'] for r in overlap],voice=' '.join(r['voice'] for r in overlap),visual_revision=STYLE)
 s['prompt']=('One continuous 10-second shot, 16:9 landscape, cinematic historical archaeology documentary, naturalistic light, controlled camera, stable physical geometry. '+s['visual']+' Camera: '+s['camera']+' '
 'Prioritize outdoor historical landscapes, archaeology, living forests and modern polar field settings. No laboratory, white-coated scientist or indoor clinical setting. '
 'Historical scenes are illustrative sixth-century late-antique Mediterranean or European rural life: plain linen and wool tunics, cloaks, modest leather footwear, plausible stone or timber buildings and hand tools. No Tudor or pirate styling, Viking horns, plate armor, Gothic cathedrals, modern machinery or plastic in historical scenes. Modern field archaeology and polar clothing must remain visibly modern and separate. '
 'Anonymous mature people illustrate roles, never authenticated portraits or witnessed events. Show a pale but visible sun and usable daylight where requested; never total worldwide darkness, an instant dead planet, mass famine victims or a century-long unchanged ash roof. Volcanoes are unnamed mechanism illustrations, not identified proven sources of the 536 or 540 events. '
 'Wood patterns are illustrative replicas, not a ring dated 536 by eye. Ice is ordinary clear or faintly layered ice: no thick black ash band, glowing chemicals or visible sulfate proof. Sulfate and sulfur dioxide are not visible labels or interchangeable materials. Any atmospheric, isotope, timeline or terrain model is a separate explanatory model, not measured data, to scale, an actual chemical experiment or a reproduced scientific figure. No magical morphing, instant frost growth, time-lapse, collapsed empires, disease transmission montage, human remains, suffering or medical procedures. '
 'No children, infants, adolescents, minors, child portraits, minors in backgrounds, screens, shadows or reflections. All visible people and hands must be clearly adult age 35–65; this is a casting instruction, not a claim about the historical population. '
 'No lip-sync, readable text, letters, dates, numbers, captions, map labels, signs, logos or watermark. '+silent)
assert len(shots)==150 and len({s['prompt'] for s in shots})==150
for i in range(0,150,10):(P/f'PROMPT_{i//10+1:02}_{i+1:03}-{i+10:03}.txt').write_text('\n\n'.join(f"{s['id']:03}. {s['prompt']}" for s in shots[i:i+10])+'\n')
voice_rows=[{k:r[k] for k in ['id','start','end','voice']} for r in rows]
dump(S/'en-US.json',voice_rows);dump(D/'ENGLISH_CUES_134.json',voice_rows);dump(D/'ALL_PROMPTS.json',shots);dump(D/'OPENING_10_SHOTS_30s.json',shots[:10]);dump(D/'BACKUP_142_150.json',shots[141:])
chapters=[]
for i in range(13):
 g=rows[i*10:(i+1)*10] if i<12 else rows[120:]
 chapters.append(dict(id=i+1,start=g[0]['start'],end=g[-1]['end'],source_cue_ids=[r['id'] for r in g],voice=' '.join(r['voice'] for r in g)))
assert [c['end']-c['start'] for c in chapters]==[100]*12+[132]
dump(D/'CHAPTERS_13.json',chapters)
(D/'KICH_BAN_EN_22m12s.txt').write_text('\n\n'.join(r['voice'] for r in rows)+'\n')
(D/'KICH_BAN_EN_CO_MOC.txt').write_text('\n\n'.join(f"{r['id']:03} | {stamp(r['start'])} → {stamp(r['end'])}\n{r['voice']}" for r in rows)+'\n')
(D/'en-US.srt').write_text('\n\n'.join(f"{r['id']}\n{stamp(r['start'])} --> {stamp(r['end'])}\n{r['voice']}" for r in rows)+'\n')
fields=['id','start','end','use_seconds','generation_seconds','voice_cue_ids','voice','source_filename','kind','setting','visual','camera','prompt']
for name,selected in [('TIMELINE_141_CANH.csv',shots[:141]),('PROMPT_INDEX_150.csv',shots)]:
 with (D/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(selected)
for name in ['NGUON_KIEM_CHUNG.md','PHAN_TICH_VA_KE_HOACH_DUNG.md','5_TIEU_DE_VA_THUMBNAIL.txt','PRODUCTION_STEPS_APPLIED.md','VOICE_PROFILES_LOCKED_BASELINE.json','MELO_SOURCE_LOCK.json']:shutil.copyfile(R/name,D/name)
words=sum(len(re.findall(r"\b[\w'-]+\b",r['voice'])) for r in rows)
qa=dict(status='passed',topic_id='MOI-053',catalogue_id='new-100-topics-20261116',target_seconds=TARGET,english_words=words,english_wpm=round(words/(TARGET/60),3),english_cues=134,ten_second_cues=133,final_cue_seconds=2,unique_prompts=150,prompt_txt_files=15,prompts_per_txt=10,timeline_shots=141,backup_prompt_ids=[142,143,144,145,146,147,148,149,150],timeline_total_seconds=TARGET,opening_shots=10,opening_seconds=30,all_prompts_silent_suffix=all(s['prompt'].endswith(silent) for s in shots),all_prompts_exclude_minors=True,translated_chapters=13,chapter_seconds=[100]*12+[132],expected_audio_frames_48000=FRAMES,requested_voice_count=16,all_requested_voices_male=True,vietnamese_voice_id='vi-VN-NamMinhNeural',voices_generated=False,footage_generated=False,video_edited=False,visual_revision=STYLE,outdoor_scenes=sum(x['setting']=='outdoor' for x in shots),underwater_scenes=sum(x['setting']=='underwater' for x in shots),historical_interior_scenes=sum(x['setting']=='historical_interior' for x in shots),laboratory_scenes=0)
dump(D/'DOCUMENT_QA.json',qa)
guide=f'''MỚI-053 — NĂM 536 — 22:12

Kịch bản Anh {words} từ, {words/(TARGET/60):.1f} từ/phút; 134 mốc = 133 × 10 giây + 2 giây cuối.
150 prompt clip 10 giây trong 15 TXT × 10, SKY536_001.mp4–SKY536_150.mp4. Timeline 141 cảnh: 001–010 lấy 3 giây/cảnh, 011–140 lấy 10 giây/cảnh, 141 lấy 2 giây. Prompt 142–150 là 9 dự phòng, không cộng thêm thời lượng. CSV có mốc và ID lời tương ứng.
Toàn bộ cảnh ở ngoài trời hoặc mái hiên mở; lịch sử, khảo cổ, rừng, băng vùng cực và mô hình giải thích. Không lab, trẻ em, chữ đọc được. Mọi prompt kết “{silent}”. Khi dựng xóa âm clip và chỉ dùng voice Anh, không nhạc/SFX. Thiếu cảnh dùng video chuyển động liên quan, không ảnh đứng có chữ.
Tái hiện chỉ minh họa. Không đêm đen toàn cầu, xác định chắc núi lửa 536/540, dải tro đen trong lõi băng, vòng cây tự ghi năm hoặc chuỗi núi lửa tự gây dịch hạch/sụp đổ đế chế. Tách 536 và khoảng 540. Mô hình không phải dữ liệu đo. Xem nguồn và giới hạn trong NGUON_KIEM_CHUNG.md.
Giữ 16 giọng nam đã lưu, gồm Andrew và Nam Minh. Backend online khóa của Melo-Viet-Studio 1.3.1 / Microsoft Edge qua edge-tts; không UI Windows hoặc model Melo đa ngôn ngữ cục bộ. Không đổi cao độ. Mỗi MP3 phải giải mã đúng 63.936.000 mẫu mono 48 kHz = 1.332 giây. Anh căn 134 mốc; các ngôn ngữ khác căn 13 chương, 12 × 100 giây + 132 giây cuối, không đồng bộ từng từ. SRT dịch theo chương cần chia nhỏ trước khi hiển thị.
Các bản nước ngoài là chuyển thể gọn giữ ý chính và giới hạn bằng chứng, không dịch từng câu toàn bộ Anh. Bản Việt viết lại toàn bộ; các bản khác dịch tự động rồi rà chọn lọc. Chưa kiểm nghe/biên tập bản ngữ độc lập. Chưa tạo footage, thumbnail hoặc MP4.
'''
(D/'HUONG_DAN_SU_DUNG.txt').write_text(guide)
(D/'README.md').write_text(f'''# MỚI-053 — Năm 536 — 22:12

[Tài liệu]({BASE}{PREFIX}_TAI_LIEU_22m12s.zip) · [15 TXT prompt]({BASE}{PREFIX}_PROMPT_15_TXT.zip) · [Kịch bản Anh]({BASE}KICH_BAN_EN_22m12s.txt) · [5 tiêu đề và thumbnail]({BASE}5_TIEU_DE_VA_THUMBNAIL.txt)

Kịch bản mới {words} từ, {words/(TARGET/60):.1f} từ/phút, 134 mốc. Điều tra ghi chép, vòng cây và lõi băng để nối bầu trời mờ với biến cố khí quyển; tách 536 và khoảng 540, không quy mọi khủng hoảng thế kỷ VI về một vụ phun trào. Đọc NGUON_KIEM_CHUNG.md về nguồn, phạm vi đọc và mức độ chắc chắn.

150 prompt/15 TXT × 10. Timeline 141 cảnh, mở 10 × 3 giây, thân 130 × 10 giây, cuối 2 giây. 142–150 dự phòng. Cảnh ngoài trời/mái hiên mở, không lab/trẻ em/chữ/âm thanh/lời nói. Hình và mô hình chỉ minh họa, chưa tạo footage, thumbnail hoặc MP4.

Giữ 16 ID nam, Andrew cho Anh và Nam Minh cho Việt. Tài liệu phát hành trước audio; chỉ báo đủ sau kiểm giải mã từng MP3 1.332 giây. Backend online khóa của Melo-Viet-Studio 1.3.1 / Microsoft Edge qua edge-tts, không chạy UI Windows/model Melo đa ngôn ngữ cục bộ. Bản nước ngoài chuyển thể 13 chương (12 × 100 + 132 giây), chưa kiểm nghe/biên tập bản ngữ độc lập.
''')
with zipfile.ZipFile(R/f'{PREFIX}_TAI_LIEU_22m12s.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(D.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(D))
with zipfile.ZipFile(R/f'{PREFIX}_PROMPT_15_TXT.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(P.glob('*.txt')):z.write(p,p.name)
print(json.dumps(qa,ensure_ascii=False),flush=True)
