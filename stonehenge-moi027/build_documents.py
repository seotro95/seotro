import csv,json,re,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';P=D/'PROMPTS';S=R/'voice/scripts'
for p in [D,P,S]:p.mkdir(parents=True,exist_ok=True)
TARGET=1292;FRAMES=62016000;PREFIX='STONEHENGE_MOI027';TAG='stonehenge-moi-027-21m32s';STYLE='archaeology-and-Neolithic-outdoor-v1'
BASE=f'https://github.com/seotro95/seotro/releases/download/{TAG}/'
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def stamp(s):return f'{s//3600:02}:{s%3600//60:02}:{s%60:02},000'
raw=[x.split('\t') for x in (R/'CUES_MASTER.tsv').read_text(encoding='utf-8').splitlines()]
assert len(raw)==130 and all(len(r)==4 for r in raw)
rows=[dict(id=int(i),start=(int(i)-1)*10,end=min(int(i)*10,TARGET),voice=v,visual=h,camera=c) for i,v,h,c in raw]
rows[86]['voice']='Our reconstruction keeps the supports in view. That makes the explanation clearer: every change in height depends on a surface carrying the weight before the next movement.'
assert [r['id'] for r in rows]==list(range(1,131)) and sum(r['end']-r['start'] for r in rows)==TARGET
opening=[
 ('Plant-fibre rope tightens beside a secured rough stone replica on a timber sledge in a Neolithic outdoor reconstruction, slight controlled motion.','Low 100 mm macro tracking along rope fibres toward the runner.'),
 ('A massive pale sarsen-like boulder on open southern English grassland, no people or extraction machinery.','Wide low arc revealing the boulder against the horizon.'),
 ('Jointed natural rock pillars in an illustrative Welsh upland outcrop, damp grass and distant ridges.','Slow close vertical tilt along a natural fissure.'),
 ('A recumbent pale-greenish sandstone replica on open chalk grassland, kept separate from tall pale uprights.','Low oblique slide across sandstone texture.'),
 ('A secured stone replica on a timber sledge rests on a stationary timber slipway, no turning rollers.','Ground-level macro slide showing runner contact.'),
 ('A wide valley and a river crossing in a schematic Neolithic landscape, no asserted confirmed transport route.','Elevated forward glide following the ground contours.'),
 ('An outdoor physical stonehole cutaway model with a stable upright base and small packing stones, no actual transparent ground.','High oblique close arc revealing the buried support model.'),
 ('A stone tenon replica beside a matching lintel recess replica on natural ground, both stationary.','Macro focus pull between projection and recess.'),
 ('An illustrative lintel replica fully resting on a stable timber crib outdoors, no load suspended over people.','Low side arc keeping every support visible.'),
 ('A completed Stonehenge-inspired trilithon on open chalk grassland at dawn, no people or modern signs.','Slow wide pullback revealing the surrounding plain.')]
shots=[dict(id=i,start=(i-1)*3,end=i*3,kind='opening',visual=v,camera=c,used=True) for i,(v,c) in enumerate(opening,1)]
for r in rows[3:]:shots.append(dict(id=len(shots)+1,start=r['start'],end=r['end'],kind='main',visual=r['visual'],camera=r['camera'],used=True))
assert len(shots)==137 and shots[-1]['end']==TARGET
for v,c in [
 ('Natural sarsen boulders in a broad southern English woodland-edge landscape, no exact prehistoric quarry claim.','Wide slow lateral drift under natural broken light.'),
 ('Adult Neolithic workers repair plant-fibre rope beside a stationary secured sledge in open grassland, all loads fully supported.','Medium close lateral slide across mature hands and rope.'),
 ('Weathered standing and fallen stones in an illustrative Salisbury Plain monument setting at sunset, empty open landscape.','Wide restrained arc returning to the central trilithon.')]:shots.append(dict(id=len(shots)+1,start=None,end=None,kind='backup_not_on_timeline',visual=v,camera=c,used=False))
silent='Video không có âm thanh, không có lời nói.'
for s in shots:
    overlap=[r for r in rows if s['used'] and r['start']<s['end'] and r['end']>s['start']]
    s.update(generation_seconds=10,use_seconds=s['end']-s['start'] if s['used'] else 0,source_filename=f'STONEHENGE_{s["id"]:03}.mp4',voice_cue_ids=[r['id'] for r in overlap],voice=' '.join(r['voice'] for r in overlap),visual_revision=STYLE)
    s['prompt']=('One continuous 10-second shot, 16:9 landscape, cinematic archaeological documentary, natural light, realistic stone and timber textures, restrained camera motion. '+s['visual']+' Camera: '+s['camera']+' '
      'All scenes are outdoors. Historical reconstructions use Neolithic Britain, plain earth-tone plant-fibre or wool clothing, plausible stone tools, wooden levers, timber sledges and plant-fibre ropes. Modern outdoor experimental archaeology uses plain field clothing only when explicitly requested in this scene. '
      'Keep the load supported and secured, material identity stable and movement small and physically credible. Stationary timber slipways do not rotate; loose rollers appear only when explicitly contrasted. Raising frames, cribs, ramps, boats and routes are possible illustrative reconstructions, not a recovered complete blueprint or a confirmed original journey. '
      'Outcrop scenes, replicas, terrain reliefs, cutaways and miniature models are explanatory illustrations, never authenticated archaeological specimens, actual LiDAR, measured data or a claimed reproduction of a recorded experiment. No exact source quarry or transport corridor is asserted by the image. '
      'No children, infants, adolescents, minors, child portraits, or minors in backgrounds, screens, shadows or reflections. Every visible person or hand must be clearly adult age 35–65. '
      'No laboratory interiors, scientists in laboratories, white coats, microscopes, electronic instruments, modern cranes, engines, Roman architecture, iron-age machinery, aliens, glowing stones, floating loads, unsupported stones over people, time-lapse, morphing, lip-sync, readable text, captions, logos or watermarks. '+silent)
assert len(shots)==140 and len({s['prompt'] for s in shots})==140
for i in range(0,140,10):(P/f'PROMPT_{i//10+1:02}_{i+1:03}-{i+10:03}.txt').write_text('\n\n'.join(f"{s['id']:03}. {s['prompt']}" for s in shots[i:i+10])+'\n',encoding='utf-8')
voice_rows=[{k:r[k] for k in ['id','start','end','voice']} for r in rows]
dump(S/'en-US.json',voice_rows);dump(D/'ENGLISH_CUES_130.json',voice_rows);dump(D/'ALL_PROMPTS.json',shots)
dump(D/'OPENING_10_SHOTS_30s.json',shots[:10]);dump(D/'BACKUP_138_140.json',shots[137:])
chapters=[]
for i in range(0,130,10):
    g=rows[i:i+10];chapters.append(dict(id=i//10+1,start=g[0]['start'],end=g[-1]['end'],source_cue_ids=[r['id'] for r in g],voice=' '.join(r['voice'] for r in g)))
assert [c['end']-c['start'] for c in chapters]==[100]*12+[92]
dump(D/'CHAPTERS_13.json',chapters)
(D/'KICH_BAN_EN_21m32s.txt').write_text('\n\n'.join(r['voice'] for r in rows)+'\n',encoding='utf-8')
(D/'KICH_BAN_EN_CO_MOC.txt').write_text('\n\n'.join(f"{r['id']:03} | {stamp(r['start'])} → {stamp(r['end'])}\n{r['voice']}" for r in rows)+'\n',encoding='utf-8')
(D/'en-US.srt').write_text('\n\n'.join(f"{r['id']}\n{stamp(r['start'])} --> {stamp(r['end'])}\n{r['voice']}" for r in rows)+'\n',encoding='utf-8')
fields=['id','start','end','use_seconds','generation_seconds','voice_cue_ids','voice','source_filename','kind','visual','camera','prompt']
for name,selected in [('TIMELINE_137_CANH.csv',shots[:137]),('PROMPT_INDEX_140.csv',shots)]:
    with (D/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(selected)
for name in ['NGUON_KIEM_CHUNG.md','PHAN_TICH_VA_KE_HOACH_DUNG.md','5_TIEU_DE_VA_THUMBNAIL.txt','PRODUCTION_STEPS_APPLIED.md','VOICE_PROFILES_LOCKED_BASELINE.json','MELO_SOURCE_LOCK.json']:shutil.copyfile(R/name,D/name)
words=sum(len(re.findall(r"\b[\w'-]+\b",r['voice'])) for r in rows)
qa=dict(status='passed',topic_id='MOI-027',catalogue_id='new-100-topics-20261116',target_seconds=TARGET,english_words=words,english_cues=130,ten_second_cues=129,final_cue_seconds=2,unique_prompts=140,prompt_txt_files=14,prompts_per_txt=10,timeline_shots=137,backup_prompt_ids=[138,139,140],timeline_total_seconds=TARGET,opening_shots=10,opening_seconds=30,all_prompts_silent_suffix=all(s['prompt'].endswith(silent) for s in shots),all_prompts_exclude_minors=True,translated_chapters=13,chapter_seconds=[100]*12+[92],expected_audio_frames_48000=FRAMES,requested_voice_count=16,all_requested_voices_male=True,vietnamese_voice_id='vi-VN-NamMinhNeural',voices_generated=False,footage_generated=False,video_edited=False,visual_revision=STYLE,outdoor_scenes=140,laboratory_scenes=0)
dump(D/'DOCUMENT_QA.json',qa)
guide=f'''MỚI-027 — STONEHENGE — 21:32

Kịch bản Anh: {words} từ; 129 mốc × 10 giây + mốc cuối 2 giây = 1.292 giây.
140 prompt clip 10 giây, chia 14 TXT × 10. Tên clip STONEHENGE_001.mp4 đến STONEHENGE_140.mp4.
Timeline dùng 137 cảnh: 001–010 lấy 3 giây/cảnh, 011–136 lấy 10 giây/cảnh, 137 lấy 2 giây. Prompt 138–140 dự phòng, không cộng vào phim. CSV ghi ID voice giao từng cảnh.
140 cảnh ngoài trời: cảnh quan, khảo cổ, phục dựng Anh thời Đá mới, mô hình vật lý và một số thử nghiệm khảo cổ ngoài trời. Không cảnh phòng thí nghiệm. Không trẻ em, kể cả nền, màn hình và phản chiếu; người/tay phải rõ trưởng thành 35–65 tuổi.
Mỗi prompt kết bằng “{silent}”. Khi dựng vẫn xóa âm gốc nếu công cụ tự sinh tiếng. Phim chính chỉ voice Anh, không nhạc/SFX. Thiếu cảnh dùng video liên quan, không ảnh đứng có chữ.
Nguồn đá, tuyến và kỹ thuật dựng là ba câu hỏi khác nhau. Không biến thử nghiệm thành lời giải duy nhất. West Woods là vùng nguồn có xác suất cao cho nhóm sarsen chính; Altar Stone là sandstone gắn vùng địa chất đông bắc Scotland, chưa chốt mỏ hay đường đi. Mọi phục dựng, mặt cắt và bản đồ mô hình chỉ minh họa, không dữ liệu khảo sát thật. Xem NGUON_KIEM_CHUNG.md.
Giữ 16 giọng nam đã khóa: Anh Andrew, Việt Nam Nam Minh, Đức Christoph. Dùng backend online của Melo-Viet-Studio 1.3.1 theo commit và SHA trong MELO_SOURCE_LOCK.json, không phải chạy UI Windows hay model Melo đa ngôn ngữ cục bộ.
Mỗi MP3 cần giải mã đúng 62.016.000 mẫu mono 48 kHz = 21:32. Anh căn 130 mốc; bản dịch căn 13 chương: 12 × 100 giây + 92 giây. Cùng độ dài không có nghĩa từng từ trùng thời điểm. SRT bản dịch theo chương cần chia nhỏ trước khi hiển thị.
Chưa kiểm nghe bản ngữ độc lập. Chưa tạo footage, thumbnail hoặc MP4.
'''
(D/'HUONG_DAN_SU_DUNG.txt').write_text(guide,encoding='utf-8')
(D/'README.md').write_text(f'''# MỚI-027 — Stonehenge — 21:32

[Tải tài liệu]({BASE}{PREFIX}_TAI_LIEU_21m32s.zip) · [Kịch bản Anh]({BASE}KICH_BAN_EN_21m32s.txt) · [5 tiêu đề/thumbnail]({BASE}5_TIEU_DE_VA_THUMBNAIL.txt)

Kịch bản nguyên bản {words} từ, ba cuộc điều tra: nguồn đá, tuyến vận chuyển, kỹ thuật dựng. 140 prompt trong 14 TXT × 10, gồm 137 cảnh timeline và 3 cảnh dự phòng. Mở đầu 10 × 3 giây, thân 126 × 10 giây, cuối 2 giây. Toàn bộ cảnh ngoài trời, không trẻ em, không tiếng hay lời nói trong clip.

Nguồn nghiên cứu, phạm vi đã đọc và các giới hạn được ghi trong NGUON_KIEM_CHUNG.md. Thử nghiệm không chứng minh một phương án duy nhất; hình phục dựng chỉ minh họa.

Tài liệu được phát hành trước audio. 16 giọng nam giữ nguyên ID đã lưu. Mỗi giọng chỉ công bố hoàn tất sau khi render và giải mã đủ 1.292 giây. Backend online Melo-Viet-Studio 1.3.1 đã khóa mã nguồn; không tự nhận chạy UI Windows. Chưa kiểm nghe bản ngữ độc lập. Chưa tạo footage, thumbnail hoặc MP4.
''',encoding='utf-8')
with zipfile.ZipFile(R/f'{PREFIX}_TAI_LIEU_21m32s.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(D.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(D))
with zipfile.ZipFile(R/f'{PREFIX}_PROMPT_NGOAI_TROI_14_TXT.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(P.glob('*.txt')):z.write(p,p.name)
print(json.dumps(qa,ensure_ascii=False),flush=True)
