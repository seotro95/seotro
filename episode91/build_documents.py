import csv,json,re,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';P=D/'PROMPTS';V=R/'voice/scripts'
for p in [D,P,V]:p.mkdir(parents=True,exist_ok=True)
TARGET=1332;FRAMES=63936000;PREFIX='SAQQAQ_HAIR_91';TITLE='The Hair That Changed Arctic History';TAG='saqqaq-hair-video-91-22m12s';BASE=f'https://github.com/seotro95/seotro/releases/download/{TAG}/'
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def stamp(t):return f'{t//3600:02}:{t%3600//60:02}:{t%60:02},000'
negative=' Use one main action and one deliberate camera movement; realistic materials, scale, natural lighting and shadows. No cuts, morphing, time-lapse or dramatic new artifact discovery. Landscapes and laboratories are generic illustrations, never authenticated excavation footage or a proven ancient journey. Hair fibers, sediment sections, globes and molecular models are explicitly manufactured teaching props. Molecular animations are schematic explanations, not measured data, a real sequence or an authenticated ancestry model. Every person and visible hand must be unmistakably mature, aged 35–65, in contemporary practical clothing; no reenactment or portrait of the ancient hair owner. No children, infants, adolescents, minors, child-sized or child-like people anywhere, including backgrounds, silhouettes, reflections, shadows, screens, photographs, artwork and miniature figures. No readable text, captions, letters, digits, labels, dates, flags, logos, watermarks, fabricated laboratory results, gene sequences, ancestry percentages or exact migration routes. No actual human remains, complete bodies, face reconstruction, violence or suffering. Closed mouths; no speech, dialogue, narration, singing, lip-sync, music, sound effects or audio stream. Video không có lời nói và không có âm thanh'
def prose_spacing(s):
 protected=re.compile(r'(https?://\S+|vi-VN-NamMinhNeural|productions/\S+|codex/\S+)')
 pieces=protected.split(s)
 fixes={'trẻem':'trẻ em','thiếuniên':'thiếu niên','nghìnnăm':'nghìn năm','phimchính':'phim chính','voiceAnh':'voice Anh','âmclip':'âm clip','khôngnhạc':'không nhạc','đúngID':'đúng ID','IDprompt':'ID prompt','IDmốc':'ID mốc','promptmới':'prompt mới','giâyđầu':'giây đầu','từAnh':'từ Anh','phươngngữ':'phương ngữ','minhhọa':'minh họa','giáocụ':'giáo cụ','bảnsao':'bản sao','backendMelo':'backend Melo','côngcụ':'công cụ','niênđại':'niên đại','bảnngữ':'bản ngữ','thờilượng':'thời lượng','giọngkhác':'giọng khác','tậpchưa':'tập chưa','môhình':'mô hình','dữliệu':'dữ liệu'}
 for i,x in enumerate(pieces):
  if i%2:continue
  for a,b in fixes.items():x=x.replace(a,b)
  x=re.sub(r'(?<=[A-Za-zÀ-ỹ])(?=\d)',' ',x);x=re.sub(r'(?<=\d)(?=[A-Za-zÀ-ỹ])',' ',x)
  x=re.sub(r',(?=\S)',', ',x);x=re.sub(r';(?=\S)','; ',x)
  pieces[i]=x
 return ''.join(pieces).replace('.mp 4','.mp4').replace('MP 4','MP4').replace('k Hz','kHz').replace('4, 000','4,000')
rows=[];prompts=[]
for line in (R/'SCENES_DRAFT.tsv').read_text().splitlines():
 ident,voice,visual=line.split('|',2);sid=int(ident);assert sid==len(rows)+1;start=(sid-1)*10;end=min(start+10,TARGET)
 if visual.startswith('REUSE:'):
  source=int(visual.split(':')[1]);assert source<sid;earlier=rows[source-1];pid=earlier['prompt_id'];visual=earlier['visual'];action='REUSE'
 else:
  source=None;pid=len(prompts)+1;action='CREATE';prompt='Create one continuous moving 10-second shot, 16:9, cinematic science-documentary photography or clearly specified explanatory animation. '+visual+negative
  prompts.append({'id':pid,'source_cue':sid,'voice_context':voice,'visual':visual,'prompt':prompt})
 rows.append({'id':sid,'start':start,'end':end,'voice':voice,'visual':visual,'prompt_id':pid,'action':action,'reuse_from_cue':source,'use_seconds':end-start})
assert len(rows)==134 and len(prompts)==120 and sum(x['action']=='REUSE' for x in rows)==14
assert rows[-1]['end']==TARGET and rows[-1]['use_seconds']==2 and all(a['end']==b['start'] for a,b in zip(rows,rows[1:]))
dump(D/'SCENES_AND_PROMPTS.json',rows);dump(D/'ALL_PROMPTS.json',prompts);dump(V/'en-US.json',rows)
titles=['The strand and the Arctic question','The archaeological context and archive','How biological traces survived','Dating hair and marine carbon','Authenticating an ancient human signal','From mitochondrial clues to a nuclear genome','Siberian affinities and model limits','An Arctic landscape without an invented journey','Archaeological traditions and genetic histories','How the2019study widened the network','Trait predictions are not a portrait','A second biochemical layer','Beyond a single individual','Returning to the strand']
chapters=[]
for i in range(14):
 group=rows[i*10:min((i+1)*10,len(rows))];chapters.append({'id':i+1,'start':group[0]['start'],'end':group[-1]['end'],'title':titles[i],'voice':' '.join(x['voice'] for x in group)})
assert [c['end']-c['start'] for c in chapters]==[100]*13+[32];dump(D/'CHAPTERS_14.json',chapters)
(D/'KICH_BAN_EN_22m12s.txt').write_text(TITLE+'\n\n'+'\n\n'.join(f"{x['id']:03} | {stamp(x['start'])}–{stamp(x['end'])}\n{x['voice']}" for x in rows)+'\n',encoding='utf-8-sig')
(D/'en-US.txt').write_text('\n\n'.join(x['voice'] for x in rows)+'\n');(D/'en-US.srt').write_text('\n\n'.join(f"{x['id']}\n{stamp(x['start'])} --> {stamp(x['end'])}\n{x['voice']}" for x in rows)+'\n')
for i in range(12):
 group=prompts[i*10:(i+1)*10];(P/f'{PREFIX}_PROMPTS_{i+1:02}_{group[0]["id"]:03}_{group[-1]["id"]:03}.txt').write_text('\n\n'.join(f"{x['id']:03}. {x['prompt']}" for x in group)+'\n',encoding='utf-8-sig')
with (D/'TIMELINE_134_CANH.csv').open('w',newline='',encoding='utf-8-sig') as f:
 fields=['id','start','end','prompt_id','action','reuse_from_cue','use_seconds','voice','visual'];w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
(D/'CAC_CANH_DUNG_LAI.txt').write_text('14 MỐC DÙNG LẠI — KHÔNG TẠO LẠI CLIP\n\n'+'\n'.join(f"Mốc {x['id']:03} {stamp(x['start'])}–{stamp(x['end'])}: dùng clip {x['prompt_id']:03}.mp4 của mốc {x['reuse_from_cue']:03}, lấy {x['use_seconds']} giây." for x in rows if x['action']=='REUSE')+'\n',encoding='utf-8-sig')
cursor=0;hook=[]
for sid,t in zip([1,2,3,7,5,6,8,9,4,10],[3,3,3,3,2,3,3,3,3,4]):
 hook.append({'start':cursor,'end':cursor+t,'source_cue':sid,'prompt_id':rows[sid-1]['prompt_id'],'note':'Planned montage only. Select actual footage against the first30seconds of English narration; no added intro runtime.'});cursor+=t
assert cursor==30 and len({x['prompt_id'] for x in hook})==10;dump(D/'OPENING_10_SHOTS_30s_PLANNED.json',hook)
for n in ['NGUON_KIEM_CHUNG.md','PHAN_TICH_VIDEO_NGUON.md','VOICE_PROFILES_LOCKED_BASELINE.json','TOPICS_001_100_FROM_GITHUB.csv','5_TIEU_DE_VA_THUMBNAIL.txt','PRODUCTION_STEPS_APPLIED.md']:shutil.copyfile(R/n,D/n)
words=sum(len(re.findall(r"\b[\w'-]+\b",x['voice'])) for x in rows)
qa={'status':'passed','topic_id':91,'target_seconds':TARGET,'english_words':words,'planned_words_per_minute':round(words/(TARGET/60),1),'cues':134,'ten_second_cues':133,'final_cue_seconds':2,'unique_prompts':120,'reused_slots':14,'prompt_txt_files':12,'prompts_per_txt':10,'all_prompts_silent_suffix':all(x['prompt'].endswith('Video không có lời nói và không có âm thanh') for x in prompts),'minor_exclusion_in_every_prompt':all('No children, infants, adolescents, minors' in x['prompt'] for x in prompts),'translated_chapters':14,'chapter_seconds':[100]*13+[32],'expected_audio_frames_48000':FRAMES,'planned_video_frames_24fps':TARGET*24,'vietnamese_voice_id':'vi-VN-NamMinhNeural','all17_saved_ids_retained':True,'native_voices_expected':1,'online_voices_expected':16,'voices_generated':False,'footage_generated':False,'video_edited':False};dump(D/'DOCUMENT_QA.json',qa)
guide=f'''CHỦ ĐỀ 91 — TÓC SAQQAQ VÀ ADN BẮC CỰC — 22:12

1. Kịch bản Anh có {words:,} từ,134mốc:133mốc10giây và2giây cuối. Audio mục tiêu1.332giây=63.936.000mẫu mono48kHz.
2. Tạo120clip10giây từ12TXT trong PROMPTS,đúng10prompt/TXT. Đặt001.mp4–120.mp4 theo IDprompt,không theo IDmốc lời.
3. TIMELINE_134_CANH.csv nối lời với clip.14mốc REUSE ghi trong CAC_CANH_DUNG_LAI.txt; mốc cuối lấy2giâyclip001.
4. Mọi người/bàn tay phải rõ35–65tuổi. Không trẻem/thiếuniên trong nền,bóng,ảnh,màn hình,phản chiếu,mô hình. Không dựng người sở hữu tóc hoặc chân dung cổ. Sợi tóc và mô hình là vật liệu minh họa hiện đại,không mẫu thật,dữ liệu đo hoặc tuyến di cư đã xác nhận.
5. Mỗi prompt kết thúc “Video không có lời nói và không có âm thanh”. Không khẩu hình,nhạc/SFX. Xóa tiếng clip nếu công cụ tự thêm.
6. Khi có footage,chọn10cảnh mạnh/30giây đầu theo lờiAnh; intro nằm trong22:12. Phim chính chỉ voiceAnh. Cảnh thiếu dùng video chuyển động liên quan,không ảnh đứng/thẻ chữ.
7. Giữ17ID từ tập71: Việt đúngNamMinhNeural nam; H’môngfemale-3 nữ dùng công cụ riêng1.6.6;15giọng khác nam.16giọng online dùng backendMelo1.3.1. Không sửa audio tập cũ.
8. Anh căn134mốc;16bản dịch căn14chương chung:13×100giây+32giây cuối. Cùng thời lượng không có nghĩa từng từ đồng thời.
9. SRT hiện là kế hoạch theo lời. SRT dịch theo chương cần chia nhỏ trước khi hiển thị. Chỉ phát hành voice khi đủ lời,đúngID và giải mã mỗi MP3 đúng63.936.000mẫu48kHz.
10. Tài liệu giai đoạn này chưa chứa audio,footage hoặcMP4. Kiểm kỹ thuật không thay thế nghe/biên tập bản ngữ; phương ngữ H’mông Trắng chưa được kiểm độc lập.
11. Phân biệt công bố ty thể2008,genome nhân2010,khung lịch sử2014 và phân tích2019; epigenome có ấn bản2014. Tuổi tóc không phải tuổi di cư; mô hình không phảiGPS; một người không đại diện mọi cư dân; dự đoán tính trạng không phải ảnh thật.
'''
(D/'HUONG_DAN_SU_DUNG.txt').write_text(prose_spacing(guide),encoding='utf-8-sig')
readme=f'''# Chủ đề91 — TócSaqqaq và ADN Bắc Cực —22:12

[Tải bộ tài liệu]({BASE}{PREFIX}_TAI_LIEU_22m12s.zip) · [Kịch bản Anh]({BASE}KICH_BAN_EN_22m12s.txt) · [5tiêu đề và5promptthumbnail]({BASE}5_TIEU_DE_VA_THUMBNAIL.txt)

**{TITLE}** có{words:,}từAnh,134mốc,tổng1.332giây.120promptmới trong12TXT,đúng10prompt/TXT;14mốc dùng lại đánh dấu. Clip10giây,mốc cuối2giây. Mọi prompt cấm trẻem,thiếuniên,lời nói vàâm thanh. Nhân vật hiện đại trưởng thành; tóc vàmô hình là minh họa,không mẫu thật,dữ liệu đo hoặc chân dung xác thực.

Câu chuyện theo mẫu tócSaqqaq từQeqertasussuk qua bảo tồn,định tuổi,xác thực ADN và so sánh quần thể. Phân biệt công trình ty thể2008,genome nhân2010,nghiên cứu2014/2019 và hướng epigenetic. Không đồng nhất văn hóa với gen,tuổi mẫu với tuổi di cư,dự đoán tính trạng với ảnh,hoặc khẳng định mọi dòng tổ tiên đều biến mất.

Tài liệu phát hành trước khi tạo17voice. Giữ17ID từ tập71: ViệtNamMinhNeural nam,H’môngfemale-3 nữ qua công cụ riêng1.6.6. Anh căn134mốc,bản dịch14chương:13×100+32giây. Mỗi voice phải giải mã đúng63.936.000mẫu48kHz trước công bố. Chưa có kiểm nghe/biên tập bản ngữ độc lập hoặc xác minh phương ngữ H’mông Trắng độc lập.

Chưa có footage/MP4tập91. Mở đầu dự kiến10cảnh/30giây nằm trong22:12; phimchính chỉvoiceAnh.
'''
(D/'README.md').write_text(prose_spacing(readme))
with zipfile.ZipFile(R/f'{PREFIX}_TAI_LIEU_22m12s.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(D.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(D))
print(json.dumps(qa),flush=True)
