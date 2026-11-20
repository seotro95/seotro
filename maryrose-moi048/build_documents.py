import csv,json,re,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';P=D/'PROMPTS';S=R/'voice/scripts'
for p in [D,P,S]:p.mkdir(parents=True,exist_ok=True)
TARGET=1302;FRAMES=62496000;PREFIX='MARYROSE_MOI048';TAG='maryrose-moi-048-21m42s';STYLE='maryrose-historical-outdoors-v1'
BASE=f'https://github.com/seotro95/seotro/releases/download/{TAG}/'
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def stamp(s):return f'{s//3600:02}:{s%3600//60:02}:{s%60:02},000'
raw=[x.split('\t') for x in (R/'CUES_MASTER.tsv').read_text().splitlines()]
assert len(raw)==131 and all(len(x)==4 for x in raw)
rows=[dict(id=int(i),start=(int(i)-1)*10,end=min(int(i)*10,TARGET),voice=v,visual=h,camera=c) for i,v,h,c in raw]
assert [r['id'] for r in rows]==list(range(1,132))
opening=[
('Plain Tudor replica chest opens on the weather deck, revealing separate bowl, comb and incomplete tool handle as an illustrative grouping.','Low 85 mm push beneath the lid, fixed object identity.','outdoor'),
('Plausible mid-sixteenth-century English carrack moored in calm Solent water, high castles, no active battle.','Wide elevated lateral glide toward the Portsmouth coast.','outdoor'),
('Adult Tudor carpenter makes one deliberate pass with a complete replica plane along a secured spare timber on deck.','Close 50 mm side track revealing one thin wood shaving.','outdoor'),
('Adult modern archaeological diver records a sedimented chest corner beside wreck timbers without lifting finds.','Steady underwater 35 mm approach with realistic limited visibility.','underwater'),
('Outdoor fixed sectional model of the ship shows brick galley structures and large supported cauldrons down in the hold.','High oblique descent into the open-air teaching model.','outdoor'),
('Replica wooden eating bowl with a small abstract ownership notch on the open weather deck, no letters.','Low macro arc along the worn rim and notch.','outdoor'),
('Adult Tudor practitioner opens a replica medicine chest with separate sealed wooden containers on deck; no patient.','Close 65 mm push toward orderly containers and mature hands.','outdoor'),
('Replica boxwood nit comb beside a small personal cloth bundle under natural deck light.','Macro 100 mm focus pull across fine teeth and cloth.','outdoor'),
('Replica gimballed compass in a connected wooden support on the sterncastle, calm sea beyond.','Steady low close arc showing mechanical support and needle.','outdoor'),
('Replica boxwood still shawm lies in two storage sections beside its separate case on a deck table.','Slow 85 mm lateral track ending on wooden finger holes.','outdoor')]
shots=[dict(id=i,start=(i-1)*3,end=i*3,kind='opening',visual=v,camera=c,setting=setting,used=True) for i,(v,c,setting) in enumerate(opening,1)]
underwater={8,11,14,103,126};interior={21,35,41,42,61}
for r in rows[3:]:
 setting='underwater' if r['id'] in underwater else 'historical_interior' if r['id'] in interior else 'outdoor'
 shots.append(dict(id=len(shots)+1,start=r['start'],end=r['end'],kind='main',visual=r['visual'],camera=r['camera'],setting=setting,used=True))
assert len(shots)==138 and shots[-1]['end']==TARGET
backup=[('Closed plain Tudor replica sea chest, small wooden bowl and boxwood comb on an empty weather deck, calm Solent behind.','Low 65 mm restrained side slide across fixed objects.','outdoor'),('Modern adult diver records a small replica object beside a wreck timber, no lifting or readable slate.','Steady underwater oblique track stopping beside the object.','underwater')]
for v,c,setting in backup:shots.append(dict(id=len(shots)+1,start=None,end=None,kind='backup_not_on_timeline',visual=v,camera=c,setting=setting,used=False))
silent='Video không có âm thanh, không có lời nói.'
for s in shots:
 overlap=[r for r in rows if s['used'] and r['start']<s['end'] and r['end']>s['start']]
 s.update(generation_seconds=10,use_seconds=s['end']-s['start'] if s['used'] else 0,source_filename=f'MARYROSE_{s["id"]:03}.mp4',voice_cue_ids=[r['id'] for r in overlap],voice=' '.join(r['voice'] for r in overlap),visual_revision=STYLE)
 s['prompt']=('One continuous 10-second shot, 16:9 landscape, cinematic historical archaeology documentary, realistic wood, water, cloth and leather, restrained camera movement. '+s['visual']+' Camera: '+s['camera']+' '
 'Prioritize outdoor Tudor weather decks, Portsmouth dockside workyards, Solent shorelines and open-air physical teaching models. Show a below-deck cabin or galley only when explicitly requested. No laboratory, white-coated scientist or modern clinical room. '
 'Historical scenes are illustrative mid-sixteenth-century English carrack settings, not authenticated archival footage, a surveyed complete ship plan, an excavated assemblage or a witnessed final-day event. Plain linen and wool, modest leather jerkins, soft Tudor caps and period shoes; plausible carvel oak hull, high fore and stern castles. No pirate styling, skull flags, Union Jack, modern steering wheel, sextant, electric machinery, plastic or modern firearms in Tudor scenes. '
 'Modern archaeology, the 1982 lifting-cradle illustration and modern outdoor study trays must remain visibly modern and separate from Tudor life. Later clay-pipe fragments appear only in modern archaeological trays or later sediment layers, never used by Tudor sailors. '
 'Objects in demonstrations are replicas. Keep incomplete recovered-form objects visibly separate from complete comparison replicas; no morphing, instant restoration or metal growing from a handle. Charts and layered models are explanatory, not original recovered maps or measured data. The opening bowl-comb-tool grouping is illustrative, not a verified shared chest. Anonymous adult casting must not imitate an identified historical face. '
 'Stable geometry, object scale, hand anatomy and material identity throughout the shot. No children, infants, adolescents, minors, child portraits or minors in backgrounds, screens, shadows or reflections. Every visible person and hand must be clearly adult age 35–65; this is a casting rule, not a claim about every actual crew member. '
 'No human remains, drowning, graphic injury, medical procedure, treasure glow, explosions, rapid flooding, timelapse, lip-sync, readable text, labels, captions, logos or watermark. '+silent)
assert len(shots)==140 and len({s['prompt'] for s in shots})==140
for i in range(0,140,10):(P/f'PROMPT_{i//10+1:02}_{i+1:03}-{i+10:03}.txt').write_text('\n\n'.join(f"{s['id']:03}. {s['prompt']}" for s in shots[i:i+10])+'\n')
voice_rows=[{k:r[k] for k in ['id','start','end','voice']} for r in rows]
dump(S/'en-US.json',voice_rows);dump(D/'ENGLISH_CUES_131.json',voice_rows);dump(D/'ALL_PROMPTS.json',shots);dump(D/'OPENING_10_SHOTS_30s.json',shots[:10]);dump(D/'BACKUP_139_140.json',shots[138:])
chapters=[]
for i in range(13):
 g=rows[i*10:(i+1)*10] if i<12 else rows[120:]
 chapters.append(dict(id=i+1,start=g[0]['start'],end=g[-1]['end'],source_cue_ids=[r['id'] for r in g],voice=' '.join(r['voice'] for r in g)))
assert [c['end']-c['start'] for c in chapters]==[100]*12+[102]
dump(D/'CHAPTERS_13.json',chapters)
(D/'KICH_BAN_EN_21m42s.txt').write_text('\n\n'.join(r['voice'] for r in rows)+'\n')
(D/'KICH_BAN_EN_CO_MOC.txt').write_text('\n\n'.join(f"{r['id']:03} | {stamp(r['start'])} → {stamp(r['end'])}\n{r['voice']}" for r in rows)+'\n')
(D/'en-US.srt').write_text('\n\n'.join(f"{r['id']}\n{stamp(r['start'])} --> {stamp(r['end'])}\n{r['voice']}" for r in rows)+'\n')
fields=['id','start','end','use_seconds','generation_seconds','voice_cue_ids','voice','source_filename','kind','setting','visual','camera','prompt']
for name,selected in [('TIMELINE_138_CANH.csv',shots[:138]),('PROMPT_INDEX_140.csv',shots)]:
 with (D/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(selected)
for name in ['NGUON_KIEM_CHUNG.md','PHAN_TICH_VA_KE_HOACH_DUNG.md','5_TIEU_DE_VA_THUMBNAIL.txt','PRODUCTION_STEPS_APPLIED.md','VOICE_PROFILES_LOCKED_BASELINE.json','MELO_SOURCE_LOCK.json']:shutil.copyfile(R/name,D/name)
words=sum(len(re.findall(r"\b[\w'-]+\b",r['voice'])) for r in rows)
qa=dict(status='passed',topic_id='MOI-048',catalogue_id='new-100-topics-20261116',target_seconds=TARGET,english_words=words,english_wpm=round(words/(TARGET/60),3),english_cues=131,ten_second_cues=130,final_cue_seconds=2,unique_prompts=140,prompt_txt_files=14,prompts_per_txt=10,timeline_shots=138,backup_prompt_ids=[139,140],timeline_total_seconds=TARGET,opening_shots=10,opening_seconds=30,all_prompts_silent_suffix=all(s['prompt'].endswith(silent) for s in shots),all_prompts_exclude_minors=True,translated_chapters=13,chapter_seconds=[100]*12+[102],expected_audio_frames_48000=FRAMES,requested_voice_count=16,all_requested_voices_male=True,vietnamese_voice_id='vi-VN-NamMinhNeural',voices_generated=False,footage_generated=False,video_edited=False,visual_revision=STYLE,outdoor_scenes=sum(x['setting']=='outdoor' for x in shots),underwater_scenes=sum(x['setting']=='underwater' for x in shots),historical_interior_scenes=sum(x['setting']=='historical_interior' for x in shots),laboratory_scenes=0)
dump(D/'DOCUMENT_QA.json',qa)
guide=f'''MỚI-048 — MARY ROSE — 21:42

Kịch bản Anh {words} từ, 131 mốc: 130 × 10 giây + 2 giây cuối = 1.302 giây, khoảng {words/(TARGET/60):.1f} từ/phút.
140 prompt clip 10 giây trong 14 TXT × 10, tên MARYROSE_001.mp4 đến MARYROSE_140.mp4.
Timeline 138 cảnh: 001–010 lấy 3 giây/cảnh; 011–137 lấy 10 giây/cảnh; 138 lấy 2 giây. Prompt 139–140 là dự phòng, không cộng vào phim. CSV ghi ID lời tương ứng.
Hình ưu tiên ngoài trời, vài cabin/bếp và khảo cổ dưới nước; không lab hoặc trẻ em, kể cả nền/phản chiếu. Nhân vật và bàn tay nhìn rõ 35–65 tuổi; đây chỉ là yêu cầu casting. Không gọi hình AI là footage khảo cổ, nhân vật có thật, bản đồ/cấu trúc khảo sát chính xác hoặc sự kiện cuối đã được chứng minh.
Mọi prompt kết “{silent}”. Khi dựng xóa âm clip, chỉ dùng voice Anh, không nhạc/SFX. Thiếu cảnh dùng video chuyển động liên quan, không ảnh đứng có chữ.
Hòm bát–lược–cán dụng cụ là nhóm minh họa, không tổ hợp tìm thấy chung. Tẩu về sau không xuất hiện trong tay thủy thủ Tudor. Dụng cụ nguyên vẹn là bản sao so sánh, tách khỏi dạng cán mất kim loại. Không cướp biển, sextant, bánh lái hiện đại hoặc Union Jack.
Giữ 16 ID giọng nam từ tập trước, gồm Anh Andrew và Việt Nam Nam Minh. Dùng backend online đã khóa của Melo-Viet-Studio 1.3.1, không UI Windows hay model Melo đa ngôn ngữ cục bộ. Nhấn từ nhẹ, không đổi cao độ.
Mỗi MP3 phải giải mã đủ 62.496.000 mẫu mono 48 kHz = 21:42. Anh căn 131 mốc, bản dịch 13 chương: 12 × 100 giây + 102 giây. Cùng thời lượng không đồng nghĩa từng từ đồng bộ. SRT bản dịch theo chương cần chia nhỏ trước khi hiển thị.
Bản dịch chuyển thể gọn từ nguồn làm rõ ngữ cảnh, giữ các quan hệ và mức độ chắc chắn; xem TRANSLATION_REVIEW.json khi được phát hành. Chưa có kiểm nghe/biên tập bản ngữ độc lập. Chưa tạo footage, ảnh thumbnail hoặc MP4.
'''
(D/'HUONG_DAN_SU_DUNG.txt').write_text(guide)
(D/'README.md').write_text(f'''# MỚI-048 — Mary Rose — 21:42

[Tài liệu]({BASE}{PREFIX}_TAI_LIEU_21m42s.zip) · [14 TXT prompt]({BASE}{PREFIX}_PROMPT_14_TXT.zip) · [Kịch bản Anh]({BASE}KICH_BAN_EN_21m42s.txt) · [5 tiêu đề/thumbnail]({BASE}5_TIEU_DE_VA_THUMBNAIL.txt)

Kịch bản Anh mới {words} từ, {words/(TARGET/60):.1f} từ/phút, 131 mốc. Kể đời sống thủy thủ qua hòm đồ nghề, bếp, vật dụng ăn uống, y tế, vệ sinh, dẫn đường và giải trí. Tách nguyên nhân chìm còn tranh luận khỏi hiện vật đã xác định; nguồn và giới hạn tại NGUON_KIEM_CHUNG.md.

140 prompt trong 14 TXT × 10. Timeline 138 cảnh, mở 10 × 3 giây, thân 127 × 10 giây, cuối 2 giây. Prompt 139–140 dự phòng. Chủ yếu ngoài trời, vài cabin/bếp và khảo cổ dưới nước, không lab/trẻ em/âm thanh/lời nói. Phục dựng và bản sao chỉ minh họa.

Tài liệu phát hành trước audio. Giữ 16 giọng nam đã lưu, gồm Nam Minh. Chỉ báo hoàn tất sau khi tạo và kiểm giải mã mỗi MP3 đủ 1.302 giây. Backend online đã khóa của Melo-Viet-Studio 1.3.1; chưa kiểm nghe bản ngữ độc lập. Chưa tạo footage, ảnh thumbnail hoặc MP4.
''')
with zipfile.ZipFile(R/f'{PREFIX}_TAI_LIEU_21m42s.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(D.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(D))
with zipfile.ZipFile(R/f'{PREFIX}_PROMPT_14_TXT.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(P.glob('*.txt')):z.write(p,p.name)
print(json.dumps(qa,ensure_ascii=False),flush=True)
