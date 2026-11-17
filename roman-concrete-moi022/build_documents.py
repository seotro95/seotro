import csv,hashlib,json,re,shutil,zipfile
from pathlib import Path

R=Path(__file__).parent;D=R/'documents';P=D/'PROMPTS';S=R/'voice/scripts'
for p in [D,P,S]:p.mkdir(parents=True,exist_ok=True)
TARGET=1282;FRAMES=61536000;PREFIX='ROMAN_MOI022';TAG='roman-concrete-moi-022-21m22s'
BASE=f'https://github.com/seotro95/seotro/releases/download/{TAG}/'
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def stamp(s):return f'{s//3600:02}:{s%3600//60:02}:{s%60:02},000'
raw=[x.split('\t') for x in (R/'CUES_MASTER.tsv').read_text().splitlines()]
assert len(raw)==129 and all(len(r)==4 for r in raw)
rows=[dict(id=int(i),start=(int(i)-1)*10,end=min(int(i)*10,TARGET),voice=v,visual=h,camera=c) for i,v,h,c in raw]
assert [r['id'] for r in rows]==list(range(1,130))
assert sum(r['end']-r['start'] for r in rows)==TARGET
opening=[
 ('Close macro of a clear drop beneath a fixed modern mortar test-holder outlet; the specimen and connected tube remain softly visible.','Locked 100 mm macro, shallow focus and a restrained focus shift toward the outlet.'),
 ('Two already-split modern cylinder halves secured in a rigid holder with an unchanged narrow fissure; water passes through a connected clear tube.','Low side macro with both retaining points visible, gentle 3 cm slider move.'),
 ('One porous off-white lime-derived inclusion crossing a fixed fissure in an enlarged physical teaching model, no new deposit growth.','Oblique macro push toward the fissure-inclusion intersection.'),
 ('Two matched modern laboratory flow holders with separate collectors; one outlet drips and the other is still, all valves and tubing unchanged.','Symmetrical medium close-up with a slow lateral slide.'),
 ('Illustrative weathered Roman rubble-and-mortar wall remains in a quiet rural central Italian setting, no people or complete fantasy reconstruction.','Low wide tracking shot along the exposed rough wall core.'),
 ('A hand-sized illustrative cut mortar slice with dark binder, angular aggregate and scattered pale inclusions rests beneath a task lamp.','Overhead macro descent into the heterogeneous cut surface.'),
 ('Three sealed teaching trays containing pale lime-based material, fine dark volcanic material and coarse tuff fragments, no proportions.','Slow tabletop slider between distinct material textures.'),
 ('Transparent-sided physical pore-network teaching model with a water meniscus approaching a pale inclusion through an already-open channel.','Steady side macro, small physically plausible water movement.'),
 ('Two separate physical fissure-stage models on one bench: an open fixed gap and another with local pale mineral filling; no transformation between them.','Gentle oblique lateral dolly, visibly separated physical objects.'),
 ('Complete modest laboratory flow apparatus with fixed modern test cylinder, connected tubing and clear collector, no readable data screen.','Slow medium-wide push that establishes inlet, specimen and outlet together.')]
shots=[]
for i,(visual,camera) in enumerate(opening,1):shots.append(dict(id=i,start=(i-1)*3,end=i*3,kind='opening',visual=visual,camera=camera,used=True))
for row in rows[3:]:shots.append(dict(id=len(shots)+1,start=row['start'],end=row['end'],kind='main',visual=row['visual'],camera=row['camera'],used=True))
assert len(shots)==136 and shots[-1]['end']==TARGET
backup=[
 ('Neutral modern microscope specimen stage holding an illustrative mortar fragment with a visible pale inclusion; an adult gloved hand withdraws after positioning it.','Close side macro on the stable specimen stage, slow focus pull.'),
 ('A clearly physical model of a thick Roman rubble wall with exposed lime-based mortar and a small drainage channel at its base, no human figures.','Wide low arc around the teaching model, natural daylight.'),
 ('Three separate physical fissure teaching models with differing gap widths and moisture conditions, all geometry fixed and no visible growth of deposits.','High oblique slider comparing the three distinct models.'),
 ('A clean glass collector beneath a fixed connected laboratory outlet, gentle reflections and no droplet falling during the shot; the cracked specimen remains in view.','Locked macro with a slow focus pull between collector rim and outlet.')]
for visual,camera in backup:shots.append(dict(id=len(shots)+1,start=None,end=None,kind='backup_not_on_timeline',visual=visual,camera=camera,used=False))
historical = (R/'HISTORICAL_CUE_VISUALS.tsv').read_text(encoding='utf-8').splitlines()
historical = {int(x.split('\t')[0]):x.split('\t')[1:] for x in historical}
assert set(historical)==set(range(4,130))
opening_historical=[
 ('An illustrative cured mortar fragment with a fixed fissure on rough dark stone, a small water drop at the lower edge, Roman masonry softly visible beyond.','Locked 100 mm macro, slow focus shift from drop to fissure.'),
 ('A narrow water path within a fixed Roman-inspired mortar cutaway, no modern test equipment, no instant mineral growth.','Low side macro with a restrained lateral move.'),
 ('Porous off-white mineral particle crossing a pre-existing fissure in an enlarged physical mortar model on a plain stone base.','Oblique macro push toward the fixed intersection.'),
 ('Two separate Roman-inspired masonry cutaways, one visibly damp and one nearly dry, no measured-result claim or ancient experiment implied.','Symmetrical close view with a slow lateral slide.'),
 ('Historical reconstruction of a Roman rubble-and-mortar wall in the central Italian countryside, rough aggregate visible.','Wide low tracking shot along the wall.'),
 ('An adult Roman mason examines a cured replica mortar fragment on a simple wooden bench, earth-tone linen tunic, no modern gloves or tools.','Close side view of mature hands rotating the fragment.'),
 ('A Roman lime-kiln reconstruction with limestone nearby and modest warm interior light, no lava or explosive reaction.','Wide oblique approach toward the kiln and stone stack.'),
 ('A Roman construction courtyard with mortar trough, ceramic water jars, volcanic grains and unfinished wall, any workers clearly adult.','High oblique drift through the workyard.'),
 ('Two separate fixed-state mortar teaching cutaways, open fissure and static local mineral filling, placed apart on a rough stone bench.','Slow lateral move emphasizing physical separation.'),
 ('A historically inspired Pompeian construction courtyard with unfinished masonry and dry mineral heaps, simple period tools, no eruption or modern crew.','Slow wide push toward the unfinished wall.')]
for shot,(visual,camera) in zip(shots[:10],opening_historical):shot.update(visual=visual,camera=camera)
for shot,row in zip(shots[10:136],rows[3:]):shot.update(visual=historical[row['id']][0],camera=historical[row['id']][1])
backup_historical=[
 ('A Roman aqueduct reconstruction above a dry Mediterranean valley, natural light and period-plausible masonry, no people.','Wide elevated drift along the arches.'),
 ('Adult Roman masons carry stone fragments in simple baskets toward a partly built wall, rough linen or wool work tunics and sandals, no modern equipment.','Medium lateral tracking shot at workyard height.'),
 ('A fixed conceptual mortar section on dark stone with a pale inclusion, rough pore network and small water meniscus, no room, instruments or instant healing.','Slow oblique macro arc around the fixed cutaway.'),
 ('A quiet Roman cistern-wall reconstruction with a narrow mortar fissure and a faint damp patch, no valves or tubes and no change in crack width.','Locked low close-up with soft natural reflections.')]
for shot,(visual,camera) in zip(shots[136:],backup_historical):shot.update(visual=visual,camera=camera)
silent='Video không có âm thanh, không có lời nói.'
for shot in shots:
    shot.update(generation_seconds=10,use_seconds=shot['end']-shot['start'] if shot['used'] else 0,source_filename=f'ROMAN_{shot["id"]:03}.mp4')
    overlaps=[r for r in rows if shot['used'] and r['start']<shot['end'] and r['end']>shot['start']]
    shot.update(voice_cue_ids=[r['id'] for r in overlaps],voice=' '.join(r['voice'] for r in overlaps))
    shot['visual_revision']='historical-context-v2-no-scientists'
    shot['prompt']=('One continuous 10-second shot, 16:9 landscape, cinematic historical documentary, realistic mineral textures and restrained camera motion. '
        +shot['visual']+' Camera: '+shot['camera']+' Maintain object identity, fixed fissure geometry and natural water behavior. '
        +'Historical scenes use ancient Roman Italian architecture, workyards, simple period materials and tools; any clothing is a plain earth-tone linen or wool working tunic with period-plausible sandals. Neutral material cutaways are explanatory illustrations, not an ancient laboratory or a claim that Romans performed modern tests. Any modern reinforcement cutaway is clearly a neutral explanatory model, never an ancient Roman reinforced-concrete claim. '
        +'All reconstructions, material sections and enlarged mineral models are illustrative, never authenticated archaeological specimens, actual measured data or a claimed reproduction of a published experiment. '
        +'No children, infants, adolescents, minors, child portraits, or minors in backgrounds, screens, shadows or reflections. Any visible person or hand must be clearly adult age 35–65. '
        +'No scientists, researchers, technicians, modern laboratory interiors, microscopes, modern lab apparatus, electronic meters, monitors, white lab coats, modern gloves or modern protective clothing. No instant repair, crack faces moving together, self-rebuilding wall, glowing grains, fake graphs, numerical readouts, time-lapse, morphing, lip-sync, readable text, captions, logos or watermarks. '+silent)
assert len(shots)==140 and len({s['prompt'] for s in shots})==140
for i in range(0,140,10):
    (P/f'PROMPT_{i//10+1:02}_{i+1:03}-{i+10:03}.txt').write_text('\n\n'.join(f"{s['id']:03}. {s['prompt']}" for s in shots[i:i+10])+'\n',encoding='utf-8')
dump(S/'en-US.json',rows);dump(D/'ENGLISH_CUES_129.json',[{k:r[k] for k in ['id','start','end','voice']} for r in rows]);dump(D/'ALL_PROMPTS.json',shots)
dump(D/'OPENING_10_SHOTS_30s.json',shots[:10]);dump(D/'BACKUP_137_140.json',shots[136:])
chapters=[]
for i in range(0,129,10):
    group=rows[i:i+10];chapters.append(dict(id=i//10+1,start=group[0]['start'],end=group[-1]['end'],source_cue_ids=[r['id'] for r in group],voice=' '.join(r['voice'] for r in group)))
assert [c['end']-c['start'] for c in chapters]==[100]*12+[82]
dump(D/'CHAPTERS_13.json',chapters)
(D/'KICH_BAN_EN_21m22s.txt').write_text('\n\n'.join(r['voice'] for r in rows)+'\n',encoding='utf-8')
(D/'KICH_BAN_EN_CO_MOC.txt').write_text('\n\n'.join(f"{r['id']:03} | {stamp(r['start'])} → {stamp(r['end'])}\n{r['voice']}" for r in rows)+'\n',encoding='utf-8')
(D/'en-US.srt').write_text('\n\n'.join(f"{r['id']}\n{stamp(r['start'])} --> {stamp(r['end'])}\n{r['voice']}" for r in rows)+'\n',encoding='utf-8')
fields=['id','start','end','use_seconds','generation_seconds','voice_cue_ids','voice','source_filename','kind','visual','camera','prompt']
for name,selected in [('TIMELINE_136_CANH.csv',shots[:136]),('PROMPT_INDEX_140.csv',shots)]:
    with (D/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(selected)
for name in ['NGUON_KIEM_CHUNG.md','PHAN_TICH_VA_KE_HOACH_DUNG.md','5_TIEU_DE_VA_THUMBNAIL.txt','PRODUCTION_STEPS_APPLIED.md','VOICE_PROFILES_LOCKED_BASELINE.json','MELO_SOURCE_LOCK.json']:
    shutil.copyfile(R/name,D/name)
words=sum(len(re.findall(r"\b[\w'-]+\b",r['voice'])) for r in rows)
qa=dict(status='passed',topic_id='MOI-022',catalogue_id='new-100-topics-20261116',target_seconds=TARGET,english_words=words,
        english_cues=129,ten_second_cues=128,final_cue_seconds=2,unique_prompts=140,prompt_txt_files=14,prompts_per_txt=10,
        timeline_shots=136,backup_prompt_ids=list(range(137,141)),timeline_total_seconds=TARGET,opening_shots=10,opening_seconds=30,
        all_prompts_silent_suffix=all(s['prompt'].endswith(silent) for s in shots),all_prompts_exclude_minors=True,
        translated_chapters=13,chapter_seconds=[100]*12+[82],expected_audio_frames_48000=FRAMES,requested_voice_count=16,
        all_requested_voices_male=True,vietnamese_voice_id='vi-VN-NamMinhNeural',voices_generated=False,footage_generated=False,video_edited=False,
        visual_revision='historical-context-v2-no-scientists',scientist_scenes=False,modern_laboratory_scenes=False)
dump(D/'DOCUMENT_QA.json',qa)
guide=f'''MỚI-022 — BÊ TÔNG LA MÃ — 21:22

Kịch bản tiếng Anh: {words} từ, 129 mốc; 128 × 10 giây + 2 giây cuối = 1.282 giây.
140 prompt trong PROMPTS: 14 TXT, đúng 10 prompt mỗi tệp. Mỗi clip tạo 10 giây. Đặt tên ROMAN_001.mp4 đến ROMAN_140.mp4.
Timeline dùng 136 cảnh: 001–010 lấy 3 giây/cảnh; 011–135 lấy 10 giây/cảnh; 136 lấy 2 giây. Prompt 137–140 là bốn cảnh dự phòng, không cộng vào phim. Xem BACKUP_137_140.json và PROMPT_INDEX_140.csv.
Mốc voice 10 giây có thể giao nhiều cảnh mở đầu 3 giây; CSV ghi đủ ID lời tương ứng, không mặc định một mốc bằng một cảnh ở đoạn mở.
Mỗi prompt kết bằng “{silent}”. Không trẻ em, thiếu niên, hình trẻ trong nền/màn hình/phản chiếu. Người/tay nhìn thấy phải rõ trưởng thành 35–65 tuổi. Khi dựng vẫn xóa âm gốc nếu công cụ tạo clip tự sinh tiếng.
Phim chính chỉ voice tiếng Anh, không nhạc/SFX. Nếu thiếu cảnh, thay bằng video chuyển động liên quan, không ảnh đứng có chữ.
Hình ưu tiên bối cảnh La Mã cổ đại: công trường, thợ xây trưởng thành, tường, lò vôi, bể chứa, cầu dẫn nước và bến cảng. Đã bỏ toàn bộ cảnh nhà khoa học, phòng thí nghiệm hiện đại và thiết bị đo hiện đại. Mặt cắt/khoáng chỉ minh họa, không phải dữ liệu đo, mẫu khảo cổ thật hoặc cảnh người La Mã làm thí nghiệm hiện đại. Lời vẫn giải thích nghiên cứu hiện đại; không được gán các phép thử ấy cho người cổ. Không để khe lành ngay khi nước chạm. Hai trạng thái dùng hai mô hình riêng; thời gian thực do voice giải thích.
Thí nghiệm năm 2023 dùng mẫu hiện đại lấy cảm hứng từ vật liệu La Mã. Khe khoảng 0,5 mm; có tiền xử lý ướt/khô hai tháng trước pha dòng chảy tối đa 30 ngày. Giảm thấm không đồng nghĩa phục hồi hoàn toàn sức chịu lực. Không áp dụng cho mọi công trình/khe.
16 giọng nam giữ nguyên ID tập Upano. Tiếng Anh Andrew, Việt Nam Nam Minh, Đức Christoph. Backend online của Melo-Viet-Studio 1.3.1 ở commit khóa trong MELO_SOURCE_LOCK.json; không tự nhận chạy UI Windows hoặc model Melo đa ngôn ngữ cục bộ.
Từng MP3 phải giải mã đúng 61.536.000 mẫu mono 48 kHz = 21:22. Anh căn 129 mốc; bản dịch căn 13 chương chung: 12 × 100 giây + 82 giây. Cùng độ dài không có nghĩa từng từ trùng thời điểm. SRT dịch theo chương cần chia nhỏ trước khi hiển thị.
Chưa có kiểm nghe bản ngữ độc lập. Chưa tạo footage, thumbnail hoặc MP4 của tập này.
'''
(D/'HUONG_DAN_SU_DUNG.txt').write_text(guide,encoding='utf-8')
readme=f'''# MỚI-022 — Bê tông La Mã — 21:22

[Tải tài liệu và 14 TXT prompt]({BASE}{PREFIX}_TAI_LIEU_21m22s.zip) · [Kịch bản Anh]({BASE}KICH_BAN_EN_21m22s.txt) · [5 tiêu đề/thumbnail]({BASE}5_TIEU_DE_VA_THUMBNAIL.txt)

Kịch bản nguyên bản {words} từ, 129 cues. 140 prompt clip 10 giây trong 14 TXT × 10, gồm 136 cảnh timeline và 4 cảnh dự phòng 137–140. Mở đầu 10 × 3 giây; thân 125 × 10 giây; cuối 2 giây, tổng 21:22.

Đọc toàn văn chính nghiên cứu 2023 (Seymour và cộng sự, DOI 10.1126/sciadv.add1602), đối chiếu phương pháp, phân biệt mẫu cổ và phép thử hiện đại. Nguồn Pompeii 2025 chỉ dùng abstract và bài cơ quan tác giả đọc được. Cơ chế và giới hạn được giải thích trong NGUON_KIEM_CHUNG.md. Không tuyên bố mọi bê tông La Mã tự lành trong mọi điều kiện; giảm thấm khác khôi phục sức chịu lực hoàn toàn.

Tài liệu được phát hành trước audio đầy đủ. Kế hoạch 16 voice nam giữ ID tập Upano, gồm Andrew, Nam Minh và Christoph. Mỗi file chỉ công bố hoàn tất khi đã render và giải mã đủ 1.282 giây. Dùng backend online Melo-Viet-Studio 1.3.1 đã khóa mã nguồn; không giả chạy UI Windows.

Không trẻ em, âm thanh hoặc lời nói trong prompt. Cảnh tạo sinh chỉ minh họa, không phải dữ liệu đo, mẫu cổ thật hoặc chứng nhận tái lập thí nghiệm. Chưa có footage, thumbnail hoặc MP4.
'''
(D/'README.md').write_text(readme,encoding='utf-8')
with zipfile.ZipFile(R/f'{PREFIX}_TAI_LIEU_21m22s.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(D.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(D))
print(json.dumps(qa,ensure_ascii=False),flush=True)
