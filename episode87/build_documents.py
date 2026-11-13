import csv,hashlib,json,re,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';P=D/'PROMPTS';V=R/'voice/scripts'
for p in [D,P,V]:p.mkdir(parents=True,exist_ok=True)
TARGET=1222;FRAMES=58656000;PREFIX='SCHOENINGEN_87';TITLE='The Wooden Half of the Stone Age';TAG='schoeningen-video-87-20m22s';BASE=f'https://github.com/seotro95/seotro/releases/download/{TAG}/'
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def stamp(t):return f'{t//3600:02}:{t%3600//60:02}:{t%60:02},000'
negative=' Use one main action and one deliberate camera movement; realistic materials, anatomy, scale, natural light and shadows; no cuts, morphing, time-lapse or dramatic new artifact discovery. Locations are generic illustrative temperate European landscapes or modern research, conservation and museum spaces, never an authenticated ancient event or exact excavation plan. All ancient-looking implements are visibly manufactured modern teaching replicas, inert and resting safely on padded supports; pointed ends have blunt protective covers where visible. No weapon construction instructions, handling in attack position, aiming, flight, impact, hunting action, injury, blood, gore or suffering. Animal bone examples must be visibly manufactured adult horse teaching casts; no real remains or human skeletal material. Every person and visible hand is unmistakably mature, aged35–65, in practical contemporary clothing; no prehistoric hominin portraits or reenactors. No children, infants, adolescents, minors, child-like or child-sized people, juvenile animals, juvenile casts or juvenile remains anywhere, including backgrounds, silhouettes, reflections, shadows, screens, photographs, artwork and miniature figures. No readable text, captions, letters, numbers, labels, dates, logos, flags, watermarks, readable displays, false laboratory results, measured micrographs, exact site maps or fabricated scientific data. Teaching models are explanatory props. Closed mouths, no speech, dialogue, narration, singing, lip-sync, music, sound effects or audio stream. Video không có lời nói và không có âm thanh'
rows=[];prompts=[]
for line in (R/'SCENES_DRAFT.tsv').read_text().splitlines():
 ident,voice,visual=line.split('|',2);sid=int(ident);assert sid==len(rows)+1;start=(sid-1)*10;end=min(start+10,TARGET)
 if visual.startswith('REUSE:'):
  source=int(visual.split(':')[1]);assert source<sid;earlier=rows[source-1];pid=earlier['prompt_id'];visual=earlier['visual'];action='REUSE'
 else:
  source=None;pid=len(prompts)+1;action='CREATE';prompt='Create one continuous moving 10-second shot, 16:9, photorealistic science-documentary cinematography. '+visual+negative
  prompts.append({'id':pid,'source_cue':sid,'voice_context':voice,'visual':visual,'prompt':prompt})
 rows.append({'id':sid,'start':start,'end':end,'voice':voice,'visual':visual,'prompt_id':pid,'action':action,'reuse_from_cue':source,'use_seconds':end-start})
assert len(rows)==123 and len(prompts)==110 and sum(x['action']=='REUSE' for x in rows)==13
assert rows[-1]['end']==TARGET and rows[-1]['use_seconds']==2 and all(a['end']==b['start'] for a,b in zip(rows,rows[1:]))
dump(D/'SCENES_AND_PROMPTS.json',rows);dump(D/'ALL_PROMPTS.json',prompts);dump(V/'en-US.json',rows)
titles=['The object and the missing material world','Discovery in a mining landscape','What water preserved','Reading human choices in wood','Repair and an object biography','A broader wooden assemblage','Horses, hunting and repeated events','What experiments actually demonstrate','The changing archaeological clock','Makers, learning and cooperation','Testing attractive explanations','The missing wooden world','Returning to the silent object']
chapters=[]
for i in range(13):
 group=rows[i*10:min((i+1)*10,len(rows))];chapters.append({'id':i+1,'start':group[0]['start'],'end':group[-1]['end'],'title':titles[i],'voice':' '.join(x['voice'] for x in group)})
assert [c['end']-c['start'] for c in chapters]==[100]*12+[22];dump(D/'CHAPTERS_13.json',chapters)
(D/'KICH_BAN_EN_20m22s.txt').write_text(TITLE+'\n\n'+'\n\n'.join(f"{x['id']:03} | {stamp(x['start'])}–{stamp(x['end'])}\n{x['voice']}" for x in rows)+'\n',encoding='utf-8-sig')
(D/'en-US.txt').write_text('\n\n'.join(x['voice'] for x in rows)+'\n');(D/'en-US.srt').write_text('\n\n'.join(f"{x['id']}\n{stamp(x['start'])} --> {stamp(x['end'])}\n{x['voice']}" for x in rows)+'\n')
for i in range(11):
 group=prompts[i*10:(i+1)*10];(P/f'{PREFIX}_PROMPTS_{i+1:02}_{group[0]["id"]:03}_{group[-1]["id"]:03}.txt').write_text('\n\n'.join(f"{x['id']:03}. {x['prompt']}" for x in group)+'\n',encoding='utf-8-sig')
with (D/'TIMELINE_123_CANH.csv').open('w',newline='',encoding='utf-8-sig') as f:
 fields=['id','start','end','prompt_id','action','reuse_from_cue','use_seconds','voice','visual'];w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
(D/'CAC_CANH_DUNG_LAI.txt').write_text('13 MỐC DÙNG LẠI — KHÔNG TẠO LẠI CLIP\n\n'+'\n'.join(f"Mốc {x['id']:03} {stamp(x['start'])}–{stamp(x['end'])}: dùng clip {x['prompt_id']:03}.mp4 của mốc {x['reuse_from_cue']:03}, lấy {x['use_seconds']} giây." for x in rows if x['action']=='REUSE')+'\n',encoding='utf-8-sig')
cursor=0;hook=[]
for sid,t in zip([1,2,3,7,9,4,5,6,8,10],[3,3,3,3,2,3,3,3,3,4]):
 hook.append({'start':cursor,'end':cursor+t,'source_cue':sid,'prompt_id':rows[sid-1]['prompt_id'],'note':'Planned montage; choose actual footage against the first30seconds of English narration. Included in runtime, no added intro.'});cursor+=t
assert cursor==30 and len({x['prompt_id'] for x in hook})==10;dump(D/'OPENING_10_SHOTS_30s_PLANNED.json',hook)
for n in ['NGUON_KIEM_CHUNG.md','PHAN_TICH_VIDEO_NGUON.md','VOICE_PROFILES_LOCKED_BASELINE.json','TOPICS_001_100_FROM_GITHUB.csv','5_TIEU_DE_VA_THUMBNAIL.txt','PRODUCTION_STEPS_APPLIED.md']:shutil.copyfile(R/n,D/n)
words=sum(len(re.findall(r"\b[\w'-]+\b",x['voice'])) for x in rows)
qa={'status':'passed','topic_id':87,'target_seconds':TARGET,'english_words':words,'planned_words_per_minute':round(words/(TARGET/60),1),'cues':123,'ten_second_cues':122,'final_cue_seconds':2,'unique_prompts':110,'reused_slots':13,'prompt_txt_files':11,'prompts_per_txt':10,'all_prompts_silent_suffix':all(x['prompt'].endswith('Video không có lời nói và không có âm thanh') for x in prompts),'minor_exclusion_in_every_prompt':all('No children, infants, adolescents, minors' in x['prompt'] for x in prompts),'juvenile_exclusion_in_every_prompt':all('juvenile animals, juvenile casts or juvenile remains' in x['prompt'] for x in prompts),'translated_chapters':13,'chapter_seconds':[100]*12+[22],'expected_audio_frames_48000':FRAMES,'planned_video_frames_24fps':TARGET*24,'vietnamese_voice_id':'vi-VN-NamMinhNeural','all17_saved_ids_retained':True,'native_voices_expected':1,'online_voices_expected':16,'voices_generated':False,'footage_generated':False,'video_edited':False};dump(D/'DOCUMENT_QA.json',qa)
guide=f'''CHỦ ĐỀ 87 — SCHÖNINGEN — 20:22

1. Kịch bản Anh có {words:,} từ,123mốc:122mốc10giây và2giâycuối. Audio mục tiêu1.222giây =58.656.000mẫu mono48kHz.
2. Tạo110clip10giây từ11TXT trong PROMPTS, đúng10prompt/TXT. Đặt001.mp4–110.mp4 theo IDprompt, không theo IDmốc lời.
3. TIMELINE_123_CANH.csv nối lời với clip.13mốc REUSE ghi trong CAC_CANH_DUNG_LAI.txt; mốc cuối lấy2giâyclip001.
4. Mọi nhân vật và bàn tay phải rõ35–65tuổi. Không trẻem, thiếuniên, hìnhảnh của họ hoặc độngvật non trong nền, bóng, ảnh, màn hình, phản chiếu, mô hình. Chỉ dùng bản sao gỗ và giáo cụ xương ngựa trưởng thành có dấu chế tạo; không di cốt thật, chân dung người cổ hoặc săn giết.
5. Mỗi prompt kết thúc “Video không có lời nói và không có âm thanh”. Không khẩu hình, nhạc hoặc SFX. Xóa tiếng clip nếu công cụ tự thêm.
6. Khi có footage, chọn10cảnh mạnh trong30giâyđầu theo lời thật; intro nằm trong20:22. Phim chính chỉ voiceAnh. Thiếu cảnh dùng video chuyển động liên quan, không ảnh đứng hoặc thẻ chữ.
7. Giữ17ID từ tập71: Việt đúngNamMinhNeural nam; H’mông female-3 nữ dùng công cụ riêng1.6.6;15giọng khác nam.16giọng online dùng backendMelo1.3.1. Không sửa audio tập cũ.
8. Anh căn123mốc;16bản dịch căn13chương chung:12×100giây+22giâycuối. Cùng thời lượng không có nghĩa từng từ đồng thời.
9. SRT hiện là kế hoạch theo lời. SRT dịch theo chương cần chia nhỏ trước khi hiển thị. Chỉ phát hành voice sau khi đủ lời, đúngID và giải mã mỗi MP3 đúng58.656.000mẫu48kHz.
10. Tài liệu giai đoạn này chưa chứa audio, footage hoặcMP4. Kiểm kỹ thuật không thay thế nghe/biên tập bảnngữ; phươngngữ H’môngTrắng chưa được kiểm độc lập.
11. Niênđại: bài1997~400nghìnnăm; công bố sau~300nghìn; nghiêncứu2025 sửa về~200nghìn. Không gọi phépđo là carbon14trực tiếp trên giáo.187hiệnvậtgỗ gồm mảnh/phếliệu, không phải187giáo; tối thiểu20vũkhísănbắt và35côngcụgỗchẻ theo2024. Không gán maker/DNA/ngônngữ hay một cuộc săn duy nhất là đã xác nhận.
'''
(D/'HUONG_DAN_SU_DUNG.txt').write_text(guide,encoding='utf-8-sig')
readme=f'''# Chủ đề87 — Schöningen —20:22

[Tải bộ tài liệu]({BASE}{PREFIX}_TAI_LIEU_20m22s.zip) · [Kịch bản Anh]({BASE}KICH_BAN_EN_20m22s.txt) · [5tiêuđề và5promptthumbnail]({BASE}5_TIEU_DE_VA_THUMBNAIL.txt)

**{TITLE}**: {words:,}từAnh,123mốc,tổng1.222giây.110promptmới trong11TXT,đúng10prompt/TXT;13mốcdùnglạiđãđánhdấu.Clip10giây,mốccuối2giây.Mọi prompt cấm trẻem,thiếuniên,lời nói,âmthanh. Hình dựng là minh họa; bản sao và mô hình không phải di vật/dữ liệu đo xác thực.

Câu chuyện đi từ gỗ được bảo tồn đến dấu chế tác,sửa chữa,bộ hiện vật,săn bắt,thí nghiệm và giới hạn diễn giải. Phân biệt niên đại công bố1997~400nghìn,sau đó~300nghìn,và nghiêncứu2025~200nghìnnăm. Không nhận187hiệnvậtgỗ là187giáo hoặc20vũkhí là20thợsănđồngthời. Nhận diện người chế tác và vai trò/ngôn ngữ không được xác lập trực tiếp từ giáo.

Tài liệu phát hành trước khi tạo17voice. Giữ17nhận diện từ tập71: Việt NamMinhNeural nam,H’mông female-3 nữ dùng backendriêng1.6.6. Anh căn123mốc,bản dịch13chương:12×100giây+22giâycuối. Mỗi voice phải giải mã đúng58.656.000mẫu48kHz trước công bố.

Chưa có footage hoặcMP4tập87. Mở đầu dự kiến10cảnh/30giây nằm trong20:22;phimchính chỉvoiceAnh. Chưa có kiểm nghe/bảnngữ độc lập hoặc xác minh phươngngữH’môngTrắng độc lập.
'''
(D/'README.md').write_text(readme)
archive=R/f'{PREFIX}_TAI_LIEU_20m22s.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(D.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(D))
print(json.dumps({**qa,'archive_bytes':archive.stat().st_size}),flush=True)
