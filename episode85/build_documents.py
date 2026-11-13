import csv,hashlib,json,re,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';P=D/'PROMPTS';V=R/'voice/scripts'
for p in [D,P,V]:p.mkdir(parents=True,exist_ok=True)
TARGET=1282;FRAMES=TARGET*48000;PREFIX='HOMO_LUZONENSIS_85';TITLE='The Island Humans We Still Can’t Place';TAG='homo-luzonensis-video-85-21m22s';BASE=f'https://github.com/seotro95/seotro/releases/download/{TAG}/'
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def stamp(t):return f'{t//3600:02}:{t%3600//60:02}:{t%60:02},000'
rows=[];prompts=[]
for line in (R/'SCENES_DRAFT.tsv').read_text().splitlines():
 ident,voice,visual=line.split('|',2);sid=int(ident);assert sid==len(rows)+1;start=(sid-1)*10;end=min(start+10,TARGET)
 if visual.startswith('REUSE:'):
  source=int(visual.split(':')[1]);assert source<sid;earlier=rows[source-1];pid=earlier['prompt_id'];visual=earlier['visual'];action='REUSE'
 else:
  source=None;pid=len(prompts)+1;action='CREATE'
  prompt=f'Create one continuous moving 10-second shot, 16:9, photorealistic science-documentary cinematography. {visual} Use one main action and one deliberate camera movement; realistic materials, anatomy, scale, natural lighting and shadows; no cuts, transformations, time-lapse or dramatic reveal of a new fossil. The location is a generic illustrative tropical Philippine landscape, cave, modern research room or clearly manufactured teaching setup as specified, never an authenticated excavation or historical event. No portrait, body-size reconstruction or complete skeleton of Homo luzonensis. Every person and visible hand must be unmistakably mature, aged 35–65; modern researchers wear practical contemporary clothing. No children, infants, adolescents, minors, child-sized or child-like people, juvenile casts or juvenile remains anywhere, including backgrounds, silhouettes, reflections, shadows, screens, photographs, artwork and miniature figures. No real human remains; only specifically described visibly manufactured adult anatomical teaching models are allowed. Never reproduce the full thirteen-specimen fossil collection or the immature femur. No skulls, blood, gore, hunting, attacks, injury or suffering. No readable text, captions, letters, numbers, labels, dates, logos, flags, watermarks, readable displays, false laboratory results, measured micrographs, authentic phylogenetic trees or invented migration routes. Physical terrain and branching models are generic explanatory props, not scientific data. No speech, dialogue, narration, singing, lip-sync, music, sound effects or audio stream. Video không có lời nói và không có âm thanh'
  prompts.append({'id':pid,'source_cue':sid,'voice_context':voice,'visual':visual,'prompt':prompt})
 rows.append({'id':sid,'start':start,'end':end,'voice':voice,'visual':visual,'prompt_id':pid,'action':action,'reuse_from_cue':source,'use_seconds':end-start})
assert len(rows)==129 and len(prompts)==120 and sum(x['action']=='REUSE' for x in rows)==9
assert rows[-1]['end']==TARGET and rows[-1]['use_seconds']==2 and all(a['end']==b['start'] for a,b in zip(rows,rows[1:]))
dump(D/'SCENES_AND_PROMPTS.json',rows);dump(D/'ALL_PROMPTS.json',prompts);dump(V/'en-US.json',rows)
titles=['A small bone and a large question','How the Callao collection grew','What thirteen fossils can tell us','The evidence inside the teeth','Curves, locomotion and misleading resemblances','The clock that changed','The water barrier','The earlier evidence at Kalinga','Evolution in an island setting','Testing relationships in 2026','What genetic evidence can and cannot identify','What would change the interpretation','Returning to the island and the fragment']
chapters=[]
for i in range(13):
 group=rows[i*10:min((i+1)*10,len(rows))];chapters.append({'id':i+1,'start':group[0]['start'],'end':group[-1]['end'],'title':titles[i],'voice':' '.join(x['voice'] for x in group)})
assert [c['end']-c['start'] for c in chapters]==[100]*12+[82];dump(D/'CHAPTERS_13.json',chapters)
(D/'KICH_BAN_EN_21m22s.txt').write_text(TITLE+'\n\n'+'\n\n'.join(f"{x['id']:03} | {stamp(x['start'])}–{stamp(x['end'])}\n{x['voice']}" for x in rows)+'\n',encoding='utf-8-sig')
(D/'en-US.txt').write_text('\n\n'.join(x['voice'] for x in rows)+'\n');(D/'en-US.srt').write_text('\n\n'.join(f"{x['id']}\n{stamp(x['start'])} --> {stamp(x['end'])}\n{x['voice']}" for x in rows)+'\n')
for i in range(12):
 group=prompts[i*10:(i+1)*10];(P/f'{PREFIX}_PROMPTS_{i+1:02}_{group[0]["id"]:03}_{group[-1]["id"]:03}.txt').write_text('\n\n'.join(f"{x['id']:03}. {x['prompt']}" for x in group)+'\n',encoding='utf-8-sig')
with (D/'TIMELINE_129_CANH.csv').open('w',newline='',encoding='utf-8-sig') as f:
 fields=['id','start','end','prompt_id','action','reuse_from_cue','use_seconds','voice','visual'];w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
(D/'CAC_CANH_DUNG_LAI.txt').write_text('9 MỐC DÙNG LẠI — KHÔNG TẠO LẠI CLIP\n\n'+'\n'.join(f"Mốc {x['id']:03} {stamp(x['start'])}–{stamp(x['end'])}: dùng clip {x['prompt_id']:03}.mp4 của mốc {x['reuse_from_cue']:03}, lấy {x['use_seconds']} giây." for x in rows if x['action']=='REUSE')+'\n',encoding='utf-8-sig')
cursor=0;hook=[]
for sid,t in zip([1,2,3,5,6,7,8,9,10,4],[3,3,3,3,2,3,3,3,3,4]):
 hook.append({'start':cursor,'end':cursor+t,'source_cue':sid,'prompt_id':rows[sid-1]['prompt_id'],'note':'Planned only; select actual clips against the first30seconds of English narration. This montage does not add runtime.'});cursor+=t
assert cursor==30 and len({x['prompt_id'] for x in hook})==10;dump(D/'OPENING_10_SHOTS_30s_PLANNED.json',hook)
for n in ['NGUON_KIEM_CHUNG.md','PHAN_TICH_VIDEO_NGUON.md','VOICE_PROFILES_LOCKED_BASELINE.json','TOPICS_001_100_FROM_GITHUB.csv','5_TIEU_DE_VA_THUMBNAIL.txt']:shutil.copyfile(R/n,D/n)
words=sum(len(re.findall(r"\b[\w'-]+\b",x['voice'])) for x in rows)
qa={'status':'passed','topic_id':85,'target_seconds':TARGET,'english_words':words,'planned_words_per_minute':round(words/(TARGET/60),1),'cues':129,'ten_second_cues':128,'final_cue_seconds':2,'unique_prompts':120,'reused_slots':9,'prompt_txt_files':12,'prompts_per_txt':10,'all_prompts_silent_suffix':all(x['prompt'].endswith('Video không có lời nói và không có âm thanh') for x in prompts),'minor_exclusion_in_every_prompt':all('No children, infants, adolescents, minors' in x['prompt'] for x in prompts),'juvenile_specimen_excluded_from_every_prompt':all('Never reproduce the full thirteen-specimen fossil collection or the immature femur' in x['prompt'] for x in prompts),'translated_chapters':13,'chapter_seconds':[100]*12+[82],'expected_audio_frames_48000':FRAMES,'planned_video_frames_24fps':TARGET*24,'vietnamese_voice_id':'vi-VN-NamMinhNeural','all17_saved_ids_retained':True,'native_voices_expected':1,'online_voices_expected':16,'voices_generated':False,'footage_generated':False,'video_edited':False};dump(D/'DOCUMENT_QA.json',qa)
guide=f'''CHỦ ĐỀ 85 — HOMO LUZONENSIS — 21:22

1. Kịch bản Anh có {words:,} từ, 129 mốc: 128 mốc 10 giây và 2 giây cuối. Mục tiêu audio 1.282 giây = 61.536.000 mẫu mono ở 48 kHz.
2. Tạo 120 clip 10 giây từ 12 TXT trong PROMPTS, đúng 10 prompt/TXT. Đặt tên 001.mp4 đến 120.mp4 theo ID prompt, không theo ID mốc lời.
3. TIMELINE_129_CANH.csv nối từng mốc với clip. Có 9 mốc REUSE trong CAC_CANH_DUNG_LAI.txt. Mốc cuối lấy 2 giây từ clip 001.
4. Không có trẻ em, thiếu niên hoặc hình ảnh của họ trong nền, ảnh, bóng, phản chiếu, màn hình và mô hình. Chỉ dùng giáo cụ giải phẫu trưởng thành có dấu chế tạo rõ; không di cốt người thật hoặc mẫu chưa trưởng thành. Không phục dựng sọ, khuôn mặt, chiều cao hoặc toàn bộ cơ thể H. luzonensis.
5. Mỗi prompt kết thúc “Video không có lời nói và không có âm thanh”. Không khẩu hình, nhạc hoặc SFX. Xóa tiếng clip nếu công cụ tự thêm.
6. Khi có footage, chọn 10 cảnh mạnh trong 30 giây đầu theo lời thật; intro nằm trong 21:22. Phim chính chỉ voice Anh. Thiếu cảnh dùng video chuyển động liên quan, không ảnh đứng hoặc thẻ chữ.
7. Giữ 17 ID từ tập 71: Việt Nam Minh Neural nam; H’mông female-3 nữ dùng công cụ riêng 1.6.6; 15 giọng còn lại là nam. Dùng backend online Melo 1.3.1 cho 16 giọng. Không đổi nhãn giọng hoặc sửa audio các tập cũ.
8. Anh căn 129 mốc; 16 bản dịch căn 13 chương chung: 12 × 100 giây + 82 giây. Cùng thời lượng không có nghĩa từng từ đồng thời.
9. SRT hiện là kế hoạch theo lời. SRT dịch theo chương cần chia nhỏ trước khi hiển thị. Chỉ phát hành voice sau khi đủ lời, đúng ID và giải mã mỗi MP3 đúng 61.536.000 mẫu ở 48 kHz.
10. Tài liệu giai đoạn này chưa chứa audio, footage hoặc MP4. Kiểm kỹ thuật không thay thế nghe/biên tập bản ngữ; phương ngữ H’mông Trắng chưa được kiểm độc lập.
'''
(D/'HUONG_DAN_SU_DUNG.txt').write_text(guide,encoding='utf-8-sig')
readme=f'''# Chủ đề 85 — Homo luzonensis — 21:22

[Tải bộ tài liệu]({BASE}{PREFIX}_TAI_LIEU_21m22s.zip) · [Kịch bản Anh TXT]({BASE}KICH_BAN_EN_21m22s.txt) · [5 tiêu đề và 5 prompt thumbnail]({BASE}5_TIEU_DE_VA_THUMBNAIL.txt)

**{TITLE}** có {words:,} từ Anh, 129 mốc, tổng 1.282 giây. Có 120 prompt mới trong 12 TXT, đúng 10 prompt/TXT, và 9 mốc dùng lại được đánh dấu. Clip mới dài 10 giây; mốc cuối dùng 2 giây. Mọi prompt cấm trẻ em, thiếu niên, mẫu chưa trưởng thành, lời nói và âm thanh. Các giáo cụ, địa hình và nhân vật là minh họa, không phải dữ liệu đo hoặc khuôn mặt xác thực.

Câu chuyện đi từ mảnh xương Callao đến các câu hỏi về giải phẫu, niên đại, vượt biển và quan hệ họ hàng. Phân biệt tuổi tối thiểu ban đầu 50/67 nghìn năm với tái đánh giá 134 ± 14 nghìn năm vào năm 2023; Kalinga khoảng 709 ± 68 nghìn năm không tự xác định là H. luzonensis. Phân tích năm 2026 thiên về quan hệ với H. erectus châu Á trong bối cảnh đảo, đồng thời còn giới hạn. Không đưa ra tuyến vượt biển, chiều cao, khuôn mặt, hệ gene hoặc tổ tiên trực tiếp đã được xác nhận.

Đây là tài liệu được phát hành trước khi tạo 17 voice. Giữ đủ 17 nhận diện từ tập 71: Việt Nam Minh Neural nam; H’mông female-3 nữ dùng công cụ riêng 1.6.6. Anh sẽ căn 129 mốc; bản dịch 13 chương: 12 × 100 giây + 82 giây cuối. Mỗi voice phải giải mã đúng 61.536.000 mẫu ở 48 kHz trước khi công bố.

Chưa có footage hoặc MP4 tập 85. Mở đầu dự kiến 10 cảnh trong 30 giây, nằm trong 21:22; phim chính chỉ voice Anh. Các bản dịch/audio cần kiểm nghe bản ngữ độc lập; phương ngữ H’mông Trắng chưa được xác minh độc lập.
'''
(D/'README.md').write_text(readme)
archive=R/f'{PREFIX}_TAI_LIEU_21m22s.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(D.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(D))
print(json.dumps({**qa,'archive_bytes':archive.stat().st_size}),flush=True)
