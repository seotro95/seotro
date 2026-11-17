import csv,json,re,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';P=D/'PROMPTS';S=R/'voice/scripts'
for p in [D,P,S]:p.mkdir(parents=True,exist_ok=True)
(D/'PROMPT_INDEX_140.csv').unlink(missing_ok=True)
TARGET=1362;FRAMES=65376000;PREFIX='QANAT_MOI030';TAG='qanat-moi-030-22m42s';STYLE='qanat-historical-outdoors-v1'
BASE=f'https://github.com/seotro95/seotro/releases/download/{TAG}/'
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def stamp(s):return f'{s//3600:02}:{s%3600//60:02}:{s%60:02},000'
raw=[x.split('\t') for x in (R/'CUES_MASTER.tsv').read_text(encoding='utf-8').splitlines()]
assert len(raw)==137 and all(len(r)==4 for r in raw)
rows=[dict(id=int(i),start=(int(i)-1)*10,end=min(int(i)*10,TARGET),voice=v,visual=h,camera=c) for i,v,h,c in raw]
assert [r['id'] for r in rows]==list(range(1,138)) and sum(r['end']-r['start'] for r in rows)==TARGET
opening=[
 ('A modest stream leaves a dark historical Iranian qanat outlet into a shallow channel across dry earth, no machinery.','Low 100 mm macro push toward water emerging into sunlight.'),
 ('Irregular qanat shaft spoil rims cross a dry Iranian plain toward distant foothills, no people at exposed openings.','Wide elevated glide following the alignment uphill.'),
 ('Outdoor physical qanat cutaway with higher source on the right and lower outlet to the left, narrow gently falling gallery.','Low side slide showing the continuous downhill water path.'),
 ('Outdoor enlarged aquifer model with saturated gravel pores, no giant cavern or lake.','Macro focus pull through the fixed wet grain spaces.'),
 ('Historical Iranian qanat outlet joins a small irrigation junction beside dry field furrows, modest continuous flow.','Low tracking along water from shade toward the first furrow.'),
 ('Outdoor longitudinal model shows ground falling more steeply than a gently descending gallery until they meet downslope.','Steady side dolly revealing both fixed slopes together.'),
 ('Adult traditional qanat worker prepares a replica rope and spoil container outdoors, mature hands and simple regional clothing.','Close side slide over hands, rope and container.'),
 ('Outdoor shaft-and-gallery model with different shaft depths and separate small spoil mounds, no pumps.','High oblique arc connecting surface openings with the narrow gallery.'),
 ('A small historical Iranian irrigated orchard borders arid plain, distant foothills visible and no people.','Wide elevated pullback from cultivation toward the dry catchment.'),
 ('A modest water thread crosses a historical qanat outlet lip into daylight, unchanged earthen geometry.','Locked low macro with a slow focus shift along the stream.')]
shots=[dict(id=i,start=(i-1)*3,end=i*3,kind='opening',visual=v,camera=c,used=True) for i,(v,c) in enumerate(opening,1)]
for r in rows[3:]:shots.append(dict(id=len(shots)+1,start=r['start'],end=r['end'],kind='main',visual=r['visual'],camera=r['camera'],used=True))
assert len(shots)==144 and shots[-1]['end']==TARGET
backup=[
 ('Outdoor desert shaft-rim chain in natural side light, irregular spacing, distant foothills and no people near openings.','Wide restrained lateral glide along the alignment.'),
 ('Historical Iranian qanat outlet with a modest continuous flow into an earthen channel, no machinery or people.','Low macro side tracking from shade into sunlight.'),
 ('Outdoor physical qanat terrain section, higher collecting ground on the right, gently falling tunnel and lower outlet to the left.','Slow side arc keeping ground and gallery slopes visible.'),
 ('Adult traditional Iranian maintenance specialist examines a replica clay support ring outdoors, mature hands and simple work clothing.','Close side arc around hands and the fixed support piece.'),
 ('A modest irrigated historical Iranian field beside arid land, a narrow water channel crossing the foreground, no people.','Wide slow pullback connecting field and surrounding dry plain.'),
 ('Underground illustrative qanat gallery with a small shallow water thread and stable hand-worked walls, no people or sudden flow changes.','Low steady forward tracking beside the channel.')]
for v,c in backup:shots.append(dict(id=len(shots)+1,start=None,end=None,kind='backup_not_on_timeline',visual=v,camera=c,used=False))
silent='Video không có âm thanh, không có lời nói.'
for s in shots:
    overlap=[r for r in rows if s['used'] and r['start']<s['end'] and r['end']>s['start']]
    s.update(generation_seconds=10,use_seconds=s['end']-s['start'] if s['used'] else 0,source_filename=f'QANAT_{s["id"]:03}.mp4',voice_cue_ids=[r['id'] for r in overlap],voice=' '.join(r['voice'] for r in overlap),visual_revision=STYLE)
    s['setting']='underground' if s['visual'].startswith('Underground') else 'outdoor'
    s['prompt']=('One continuous 10-second shot, 16:9 landscape, cinematic historical engineering and archaeology documentary, natural earth and water textures, restrained camera motion. '+s['visual']+' Camera: '+s['camera']+' '
      'Prioritize outdoor Iranian dryland landscapes, archaeology, historic workyards and outdoor physical cutaway models. Show an underground gallery only when explicitly requested in this scene; galleries are narrow working passages, never palaces or huge caves. '
      'Historical scenes are illustrative preindustrial Iranian rural settings, not a verified dynasty or recorded event. Plain regional work tunics, trousers and woven headcloths where people appear; practical hand tools, earth, stone, wood, rope and clay supports. No Roman costumes, caveman clothing or ancient powered machines. Any explicitly modern well comparison is a separate teaching model, never an ancient electric-pump claim. '
      'In longitudinal cutaways keep the collecting source higher at the right and the outlet lower at the left; the gallery descends gently right to left and the ground surface can descend more steeply to meet it. Water remains on the downhill path; access shafts are not separate pumping wells. Keep geometry, water level and object identity stable throughout the shot. Aquifers are porous or fractured material, not giant empty lakes. '
      'All reconstructions, archaeological sections, terrain reliefs and replicas are explanatory illustrations, not authenticated finds, actual site surveys, measured groundwater data or a recorded experiment. Separate fixed-state models remain visibly separate, without morphing between them. '
      'No children, infants, adolescents, minors, child portraits, or minors in backgrounds, screens, shadows or reflections. Every visible person or hand must be clearly adult age 35–65. '
      'No laboratories, scientists in white coats, modern lab equipment, fake gauges, numerical readouts, glowing water, pressure fountains, upward-flowing water, giant hidden waterfall, sudden flooding, instant greening, lip-sync, time-lapse, readable text, captions, logos or watermarks. '+silent)
assert len(shots)==150 and len({s['prompt'] for s in shots})==150
for i in range(0,150,10):(P/f'PROMPT_{i//10+1:02}_{i+1:03}-{i+10:03}.txt').write_text('\n\n'.join(f"{s['id']:03}. {s['prompt']}" for s in shots[i:i+10])+'\n',encoding='utf-8')
voice_rows=[{k:r[k] for k in ['id','start','end','voice']} for r in rows]
dump(S/'en-US.json',voice_rows);dump(D/'ENGLISH_CUES_137.json',voice_rows);dump(D/'ALL_PROMPTS.json',shots)
dump(D/'OPENING_10_SHOTS_30s.json',shots[:10]);dump(D/'BACKUP_145_150.json',shots[144:])
chapters=[]
for i in range(0,137,10):
    g=rows[i:i+10];chapters.append(dict(id=i//10+1,start=g[0]['start'],end=g[-1]['end'],source_cue_ids=[r['id'] for r in g],voice=' '.join(r['voice'] for r in g)))
assert [c['end']-c['start'] for c in chapters]==[100]*13+[62]
dump(D/'CHAPTERS_14.json',chapters)
(D/'KICH_BAN_EN_22m42s.txt').write_text('\n\n'.join(r['voice'] for r in rows)+'\n',encoding='utf-8')
(D/'KICH_BAN_EN_CO_MOC.txt').write_text('\n\n'.join(f"{r['id']:03} | {stamp(r['start'])} → {stamp(r['end'])}\n{r['voice']}" for r in rows)+'\n',encoding='utf-8')
(D/'en-US.srt').write_text('\n\n'.join(f"{r['id']}\n{stamp(r['start'])} --> {stamp(r['end'])}\n{r['voice']}" for r in rows)+'\n',encoding='utf-8')
fields=['id','start','end','use_seconds','generation_seconds','voice_cue_ids','voice','source_filename','kind','visual','camera','prompt']
for name,selected in [('TIMELINE_144_CANH.csv',shots[:144]),('PROMPT_INDEX_150.csv',shots)]:
    with (D/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(selected)
for name in ['NGUON_KIEM_CHUNG.md','PHAN_TICH_VA_KE_HOACH_DUNG.md','5_TIEU_DE_VA_THUMBNAIL.txt','PRODUCTION_STEPS_APPLIED.md','VOICE_PROFILES_LOCKED_BASELINE.json','MELO_SOURCE_LOCK.json']:shutil.copyfile(R/name,D/name)
words=sum(len(re.findall(r"\b[\w'-]+\b",r['voice'])) for r in rows)
qa=dict(status='passed',topic_id='MOI-030',catalogue_id='new-100-topics-20261116',target_seconds=TARGET,english_words=words,english_cues=137,ten_second_cues=136,final_cue_seconds=2,unique_prompts=150,prompt_txt_files=15,prompts_per_txt=10,timeline_shots=144,backup_prompt_ids=[145,146,147,148,149,150],timeline_total_seconds=TARGET,opening_shots=10,opening_seconds=30,all_prompts_silent_suffix=all(s['prompt'].endswith(silent) for s in shots),all_prompts_exclude_minors=True,translated_chapters=14,chapter_seconds=[100]*13+[62],expected_audio_frames_48000=FRAMES,requested_voice_count=16,all_requested_voices_male=True,vietnamese_voice_id='vi-VN-NamMinhNeural',voices_generated=False,footage_generated=False,video_edited=False,visual_revision=STYLE,outdoor_scenes=sum(x['setting']=='outdoor' for x in shots),underground_scenes=sum(x['setting']=='underground' for x in shots),laboratory_scenes=0,english_wpm=round(words/(TARGET/60),3),previous_english_wpm=round(3568/(1292/60),3),faster_english_percent=round((words/TARGET/(3568/1292)-1)*100,2))
dump(D/'DOCUMENT_QA.json',qa)
guide=f"""MỚI-030 — QANAT — 22:42

Kịch bản Anh {words} từ, 137 mốc: 136 × 10 giây + 2 giây cuối = 1.362 giây.
150 prompt clip 10 giây trong 15 TXT × 10. Đặt tên QANAT_001.mp4 đến QANAT_150.mp4.
Timeline dùng 144 cảnh: 001–010 lấy 3 giây/cảnh; 011–143 lấy 10 giây/cảnh; 144 lấy 2 giây. Prompt 145–150 là 6 cảnh dự phòng không cộng vào phim. CSV ghi ID lời giao từng cảnh.
Nhịp Anh khoảng {words/(TARGET/60):.1f} từ/phút, nhanh hơn khoảng {(words/TARGET/(3568/1292)-1)*100:.1f}% mật độ từ/phút của tập Stonehenge. Native phrase rate +2%, khoảng nghỉ gọn, căn thời gian giữ pitch. Nội dung nhiều hơn phù hợp 22:42; không tăng tốc rồi lấp im lặng.
Phần hình ưu tiên ngoài trời: cảnh quan, khảo cổ, phục dựng Iran tiền công nghiệp và mô hình mặt cắt. Vài cảnh gallery ngầm, không lab. Không trẻ em kể cả nền/màn hình/phản chiếu; người/tay rõ trưởng thành 35–65 tuổi. Mô hình chỉ minh họa, không dữ liệu khảo sát thật.
Trong mặt cắt, nguồn bên phải cao hơn; cửa ra bên trái thấp hơn; nước không tự leo giếng. Độ dốc, độ sâu, chiều dài, lớp lót và lịch sử thay đổi tùy nơi. Ví dụ độ dốc trong lời không phải tiêu chuẩn thiết kế. Không gọi nước trong là an toàn uống hoặc coi nước là vô hạn.
Mỗi prompt kết bằng “{silent}”. Khi dựng xóa âm clip nếu công cụ tự sinh tiếng. Phim chính chỉ voice Anh, không nhạc/SFX. Thiếu cảnh dùng video chuyển động liên quan, không ảnh đứng có chữ.
Giữ 16 giọng nam đã lưu: Anh Andrew, Việt Nam Nam Minh, Đức Christoph. Backend online Melo-Viet-Studio 1.3.1 theo mã nguồn khóa, không phải chạy UI Windows hoặc model Melo đa ngôn ngữ cục bộ.
Mỗi MP3 cần giải mã đúng 65.376.000 mẫu mono 48 kHz = 22:42. Anh căn 137 mốc, bản dịch 14 chương: 13 × 100 giây + 62 giây. Cùng độ dài không có nghĩa từng từ đồng bộ; SRT chương cần chia nhỏ trước khi hiển thị. Chưa kiểm nghe bản ngữ độc lập. Chưa tạo footage, thumbnail hoặc MP4.
"""
(D/'HUONG_DAN_SU_DUNG.txt').write_text(guide,encoding='utf-8')
(D/'README.md').write_text(f"""# MỚI-030 — Qanat — 22:42

[Tài liệu]({BASE}{PREFIX}_TAI_LIEU_22m42s.zip) · [15 TXT prompt]({BASE}{PREFIX}_PROMPT_15_TXT.zip) · [Kịch bản Anh]({BASE}KICH_BAN_EN_22m42s.txt) · [5 tiêu đề/thumbnail]({BASE}5_TIEU_DE_VA_THUMBNAIL.txt)

Kịch bản nguyên bản {words} từ Anh, khoảng {words/(TARGET/60):.1f} từ/phút. Nhịp nhanh hơn một chút so với Stonehenge, vẫn đúng 22:42. Theo nguồn nước, gallery dốc nhẹ, giếng tiếp cận, cửa ra, ruộng và quản lý nguồn.

150 prompt trong 15 TXT × 10. Timeline 144 cảnh: mở 10 × 3 giây, thân 133 × 10 giây, cuối 2 giây. Prompt 145–150 dự phòng. Hình ưu tiên ngoài trời, vài gallery ngầm, không lab/trẻ em/âm thanh hoặc lời nói trong clip.

Nguồn, phạm vi đọc và giới hạn tại NGUON_KIEM_CHUNG.md. Không đồng nhất niên đại hoặc nguồn gốc mọi qanat; không hứa nước vô hạn, không chi phí hay miễn bảo trì. Hình và mô hình chỉ minh họa.

Tài liệu phát hành trước audio. Kế hoạch 16 giọng nam giữ nguyên ID đã lưu, gồm Nam Minh. Chỉ báo hoàn tất từng giọng sau khi tạo và kiểm giải mã đủ 1.362 giây. Dùng backend online đã khóa của Melo-Viet-Studio 1.3.1. Chưa kiểm nghe bản ngữ độc lập. Chưa tạo footage, thumbnail hoặc MP4.
""",encoding='utf-8')
with zipfile.ZipFile(R/f'{PREFIX}_TAI_LIEU_22m42s.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(D.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(D))
with zipfile.ZipFile(R/f'{PREFIX}_PROMPT_15_TXT.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(P.glob('*.txt')):z.write(p,p.name)
print(json.dumps(qa,ensure_ascii=False),flush=True)
