import csv,hashlib,json,re,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';D.mkdir(exist_ok=True);P=D/'PROMPTS';P.mkdir(exist_ok=True);V=R/'voice/scripts';V.mkdir(parents=True,exist_ok=True)
TARGET=1242;TITLE='The Meal That Had to Survive Tomorrow';PREFIX='FOOD_PRESERVATION_45'
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def stamp(t):return f'{t//3600:02}:{t%3600//60:02}:{t%60:02},000'
rows=[];prompts=[]
for line in (R/'SCENES_DRAFT.tsv').read_text().splitlines():
 ident,voice,visual=line.split('|',2);sid=int(ident);start=(sid-1)*10;end=min(start+10,TARGET)
 if visual.startswith('REUSE:'):
  source=int(visual.split(':')[1]);assert source<sid;earlier=rows[source-1];pid=earlier['prompt_id'];visual=earlier['visual'];action='REUSE'
 else:
  source=None;pid=len(prompts)+1;action='CREATE'
  region=('Late Pleistocene eastern Jordan when a prehistoric setting is specified; Kharaneh IV reconstructions are illustrative and not an authenticated recovered rack.' if 31<=sid<=40 else 'Qesem-related research or a generic Mediterranean limestone setting as specified; illustrative human figures do not identify a species, named individual or exact ancestral appearance.' if 51<=sid<=70 else 'Illustrative early Holocene southern Scandinavian landscape or clearly contemporary research as specified; no reconstructed recipe or exact excavated feature is claimed.' if 81<=sid<=89 else 'Illustrative early pre-pottery Neolithic southern Jordan or clearly contemporary research as specified; no claim of an exact surveyed settlement plan.' if 91<=sid<=104 else 'A generic illustrative landscape, anonymous prehistoric setting, contemporary research scene or clearly schematic teaching model as specified; never present generated material as an authenticated archaeological record.')
  prompt=f'Create one continuous moving 10-second shot, 16:9, photorealistic science-documentary cinematography. {visual} {region} Use one main action and one deliberate camera movement, realistic scale, materials and light; no cuts or rapid transformations. Every human must be unmistakably mature, aged 35–60, including any visible hands. Prehistoric adults wear practical fully covering clothing; modern researchers wear contemporary field or laboratory clothing. No children, infants, adolescents, minors, child-sized or child-like figures anywhere, including backgrounds, shadows, reflections, photos, artwork, model figures and screens. No human remains, blood, gore, butchery, animal suffering or staged disaster; any bones are clean animal specimens or clearly described replicas. No pottery, metal tools or modern packaging in prehistoric scenes. No readable text, captions, dates, numbers, logos, flags or watermarks. Do not invent authenticated maps, measured chemical results, scientific readings or archaeological layouts. Models and reconstructions illustrate principles only; checked labels are added in editing. No speech, dialogue, narration, singing, lip-sync, music, sound effects or audio stream. Video không có lời nói và không có âm thanh'
  prompts.append({'id':pid,'source_cue':sid,'voice_context':voice,'visual':visual,'prompt':prompt})
 rows.append({'id':sid,'start':start,'end':end,'voice':voice,'visual':visual,'prompt_id':pid,'action':action,'reuse_from_cue':source,'use_seconds':end-start})
assert len(rows)==125 and len(prompts)==110 and sum(x['action']=='REUSE' for x in rows)==15
assert rows[-1]['end']==TARGET and all(a['end']==b['start'] for a,b in zip(rows,rows[1:]))
dump(D/'SCENES_AND_PROMPTS.json',rows);dump(D/'ALL_PROMPTS.json',prompts);dump(V/'en-US.json',rows)
chap_titles=['The meal after the meal','The clock inside food','What moving air can change','The vanished frames of Kharaneh IV','When smoke is evidence','A container inside an animal bone','Testing a delayed meal','Cold is a condition, not a feature','Fish, seasons and a constructed store','Storage before familiar farming','Plants, roofs and accidental survival','The work behind tomorrow','A meal for tomorrow']
chapters=[]
for i in range(13):
 g=rows[i*10:min((i+1)*10,len(rows))];chapters.append({'id':i+1,'start':g[0]['start'],'end':g[-1]['end'],'title':chap_titles[i],'voice':' '.join(x['voice'] for x in g)})
dump(D/'CHAPTERS_13.json',chapters)
script=TITLE+'\n\n'+'\n\n'.join(f"{x['id']:03} | {stamp(x['start'])}–{stamp(x['end'])}\n{x['voice']}" for x in rows)+'\n'
(D/'KICH_BAN_EN_20m42s.txt').write_text(script,encoding='utf-8-sig');(D/'en-US.txt').write_text('\n\n'.join(x['voice'] for x in rows)+'\n')
(D/'en-US.srt').write_text('\n\n'.join(f"{x['id']}\n{stamp(x['start'])} --> {stamp(x['end'])}\n{x['voice']}" for x in rows)+'\n')
for i in range(11):
 g=prompts[i*10:(i+1)*10];(P/f'{PREFIX}_PROMPTS_{i+1:02}_{g[0]["id"]:03}_{g[-1]["id"]:03}.txt').write_text('\n\n'.join(f"{x['id']:03}. {x['prompt']}" for x in g)+'\n',encoding='utf-8-sig')
with (D/'TIMELINE_125_CANH.csv').open('w',newline='',encoding='utf-8-sig') as f:
 fields=['id','start','end','prompt_id','action','reuse_from_cue','use_seconds','voice','visual'];w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
reuse=[x for x in rows if x['action']=='REUSE'];(D/'CAC_CANH_DUNG_LAI.txt').write_text('15 MỐC DÙNG LẠI — KHÔNG TẠO LẠI CLIP\n\n'+'\n'.join(f"Mốc {x['id']:03} {stamp(x['start'])}–{stamp(x['end'])}: dùng clip {x['prompt_id']:03}.mp4, bối cảnh của mốc {x['reuse_from_cue']:03}; lấy {x['use_seconds']} giây." for x in reuse)+'\n',encoding='utf-8-sig')
hook_sources=[1,2,3,5,12,21,32,51,71,91];durations=[3,2,3,3,2,3,4,4,3,3];cursor=0;hook=[]
for sid,t in zip(hook_sources,durations):
 row=rows[sid-1];hook.append({'start':cursor,'end':cursor+t,'source_cue':sid,'prompt_id':row['prompt_id'],'note':'Planned only; review the actual generated footage and first30second narration before final editing.'});cursor+=t
assert cursor==30 and len({x['prompt_id'] for x in hook})==10;dump(D/'OPENING_10_SHOTS_30s_PLANNED.json',hook)
for n in ['NGUON_KIEM_CHUNG.md','PHAN_TICH_VIDEO_NGUON.md','VOICE_PROFILES_LOCKED_BASELINE.json','ADAM_VOICE_LOCK.json','TOPICS_001_100_FROM_GITHUB.csv']:shutil.copyfile(R/n,D/n)
guide='''CHỦ ĐỀ 45 — BẢO QUẢN THỨC ĂN THỜI TIỀN SỬ — 20:42

1. Đọc KICH_BAN_EN_20m42s.txt và phân tích nguồn. Có 125 mốc lời: 124 mốc 10 giây và mốc cuối 2 giây.
2. Tạo 110 clip im lặng 10 giây từ 11 TXT trong PROMPTS. Mỗi TXT có 10 prompt. Đặt tên 001.mp4 đến 110.mp4 theo ID prompt, không theo ID mốc lời.
3. TIMELINE_125_CANH.csv nối mốc lời với clip. Có 15 mốc REUSE đã đánh dấu trong CAC_CANH_DUNG_LAI.txt. Mốc cuối chỉ dùng 2 giây từ clip 001.
4. Mọi prompt cấm trẻ em và thiếu niên, kể cả nền, phản chiếu, ảnh và màn hình. Không có lời nói, nhạc, SFX hoặc audio stream; xóa hết âm thanh clip gốc nếu công cụ vẫn sinh ra tiếng.
5. Mô hình và cảnh tái dựng chỉ minh họa. Không dùng bản đồ, dữ liệu phân tích hoặc nhãn AI như hồ sơ khảo cổ thật. Địa điểm tiền gốm không có bình gốm hoặc công cụ kim loại.
6. Sau khi có footage, chọn 10 cảnh mạnh trong 30 giây đầu. Phần mở đầu nằm trong tổng 20:42, không nối thêm intro. Chỉ dùng voice Anh trong phim chính; không nhạc/SFX. Cảnh thiếu dùng video chuyển động liên quan, không ảnh tĩnh hoặc thẻ chữ.
7. Hồ sơ giọng đã ghi 16 nam và nữ H'mông female-3. Riêng Việt đổi sang preset Adam thật trong VieNeu Turbo của tool Melo + Việt 1.3.1 theo yêu cầu mới. Không đổi tên một giọng khác thành Adam.
8. Chỉ bàn giao audio sau khi tạo và giải mã kiểm tra đủ 59.616.000 mẫu mono 48 kHz cho mỗi ngôn ngữ, đúng 1.242 giây. Bản Anh theo 125 mốc; các bản dịch theo 13 chương, 12 chương 100 giây và chương cuối 42 giây.
9. SRT hiện là kế hoạch theo lời. Các SRT dịch dạng chương cần chia nhỏ trước khi hiển thị như phụ đề. Cùng tổng thời lượng không đồng nghĩa từng từ của các ngôn ngữ trùng thời điểm.
10. Bộ tài liệu chưa chứa audio đã tạo, footage hoặc MP4 hoàn chỉnh. Kiểm kỹ thuật không thay thế biên tập/nghe bản ngữ; phương ngữ H'mông Trắng chưa được xác nhận độc lập.
'''
(D/'HUONG_DAN_SU_DUNG.txt').write_text(guide,encoding='utf-8-sig')
words=sum(len(re.findall(r"\b[\w'-]+\b",x['voice'])) for x in rows)
qa={'status':'passed','topic_id':45,'target_seconds':TARGET,'english_words':words,'planned_words_per_minute':round(words/(TARGET/60),1),'cues':125,'ten_second_cues':124,'final_cue_seconds':2,'unique_prompts':110,'reused_slots':15,'prompt_txt_files':11,'prompts_per_txt':10,'all_prompts_silent_suffix':all(x['prompt'].endswith('không có âm thanh') and 'Video không có lời nói' in x['prompt'] for x in prompts),'minor_exclusion_in_every_prompt':all('No children, infants, adolescents' in x['prompt'] for x in prompts),'translated_chapters':13,'chapter_seconds':[x['end']-x['start'] for x in chapters],'expected_audio_frames_48000':59616000,'planned_video_frames_24fps':29808,'vietnamese_voice_id':'Adam','native_voices_expected':2,'online_voices_expected':15,'voices_generated':False,'footage_generated':False,'video_edited':False}
dump(D/'DOCUMENT_QA.json',qa)
base='https://github.com/seotro95/seotro/releases/download/food-preservation-video-45-20m42s/'
readme=f'''# Chủ đề 45 — Bảo quản thức ăn thời tiền sử — 20:42

[Tải bộ tài liệu]({base}FOOD_PRESERVATION_45_TAI_LIEU_20m42s.zip) · [Kịch bản Anh TXT]({base}KICH_BAN_EN_20m42s.txt)

**The Meal That Had to Survive Tomorrow**: 3.134 từ Anh, 125 mốc lời, tổng 1.242 giây. Có 110 prompt mới trong 11 TXT, 10 prompt/TXT và 15 mốc dùng lại được đánh dấu. Mỗi prompt tạo clip chuyển động 10 giây, không có trẻ em, thiếu niên, lời nói hoặc âm thanh. Mốc cuối chỉ dùng 2 giây.

Nội dung đi từ bài toán thức ăn hôm nay/bữa ăn ngày mai đến làm khô, khói, tủy ở Qesem, điều kiện lạnh, cá ở Norje Sunnansund, kho Dhra′ và thực vật Sharara. Phân biệt dấu tích, diễn giải nghiên cứu và tái dựng minh họa; không trình bày một công thức cổ đã biết chắc.

Đây là giai đoạn bàn giao kịch bản và prompt, **chưa có voice, footage hoặc MP4 tập 45**. Sau bước này mới tạo 17 voice riêng: 16 nam và nữ H'mông female-3. Bản Việt dùng đúng preset **Adam** (nam miền Nam) trong VieNeu Turbo của tool Melo + Việt 1.3.1; các nhận diện giọng còn lại giữ nguyên. Mọi audio cần giải mã đúng 59.616.000 mẫu ở 48 kHz, tương đương 20:42, trước khi công bố.

Bản Anh căn 125 mốc; các bản dịch giữ 13 ranh giới chương. Kiểm kỹ thuật không phải chứng nhận nghe bản ngữ. Khi có clip, kế hoạch mở đầu là 10 cảnh trong 30 giây, nằm trong tổng 20:42; phim chính chỉ có voice Anh.
'''
(D/'README.md').write_text(readme)
archive=R/f'{PREFIX}_TAI_LIEU_20m42s.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(D.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(D))
print(json.dumps({**qa,'archive_bytes':archive.stat().st_size}),flush=True)
