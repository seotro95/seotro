import csv,hashlib,json,re,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';D.mkdir(exist_ok=True);P=D/'PROMPTS';P.mkdir(exist_ok=True);V=R/'voice/scripts';V.mkdir(parents=True,exist_ok=True)
TITLE="When the Sea Was Land: Earth's Vanishing Bridges"
rows=[];prompts=[];created={}
for line in (R/'SCENES_DRAFT.tsv').read_text().splitlines():
 a,voice,visual=line.split('|',2);sid=int(a);start=(sid-1)*10;end=min(start+10,1352)
 if visual.startswith('REUSE:'):
  source=int(visual.split(':')[1]);assert source<sid
  earlier=rows[source-1];pid=earlier['prompt_id'];shot=earlier['visual'];action='REUSE'
 else:
  source=sid;pid=len(prompts)+1;shot=visual;action='CREATE'
  region=('Late Pleistocene Beringia, cold often dry lowlands and open habitats, anatomically modern adult humans when specified.' if 31<=sid<=50 else 'Illustrative early Holocene northwestern European lowland and North Sea environments; do not claim a specific recovered settlement.' if 51<=sid<=70 else 'Illustrative tropical Southeast Asian Pleistocene landscapes or clearly modern research when specified; no assertion of a proven migration route.' if 71<=sid<=90 else 'Natural landscape or clearly contemporary scientific demonstration as specified; all physical models are schematic, not actual research results.')
  prompt=f'Create one continuous moving 10-second shot, 16:9, photorealistic science-documentary cinematography. {shot} {region} Only one main action and one clear camera movement, physically credible water and materials. Any human must be unmistakably mature, aged 35–60; prehistoric people are generic illustrative adults in practical fully covering clothing, modern researchers use modern equipment. No children, infants, adolescents, minors, child-sized figures or child-like silhouettes anywhere, including backgrounds, reflections, photos, artwork, model figures and screens. No exposed human remains, gore, staged suffering, invented ancient cities, built land bridges or dramatic instant ice-age transformations. No readable text, numbers, captions, flags, logos or watermarks. Do not invent authenticated maps, migration arrows, dated shorelines or scientific readings; geographic labels and checked diagrams belong in editing. No speech, narration, dialogue, singing, moving lips, music, sound effects or audio stream. không có âm thanh'
  prompts.append({'id':pid,'source_cue':sid,'voice_context':voice,'visual':shot,'prompt':prompt})
 row={'id':sid,'start':start,'end':end,'voice':voice,'visual':shot,'prompt_id':pid,'action':action,'reuse_from_cue':source if action=='REUSE' else None,'use_seconds':end-start}
 rows.append(row)
assert len(rows)==136 and len(prompts)==120 and sum(x['action']=='REUSE' for x in rows)==16
assert rows[0]['start']==0 and rows[-1]['end']==1352 and all(a['end']==b['start'] for a,b in zip(rows,rows[1:]))
def stamp(t):return f'{t//3600:02}:{t%3600//60:02}:{t%60:02},000'
def dump(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
dump(D/'SCENES_AND_PROMPTS.json',rows);dump(D/'ALL_PROMPTS.json',prompts);dump(V/'en-US.json',rows)
titles=['The path beneath the water','Where the water went','Shelves, saddles and deep channels','Beringia in time','Connection and a usable route','A landscape beneath the North Sea','Doggerland and a changing ending','The expanded world of Sunda','Sahul and the water that remained','Why sea level is local','Reading a drowned landscape','Connections through repeated cycles','Human lives and a selective archive','The map is a moment']
chapters=[]
for i in range(14):
 group=rows[i*10:min((i+1)*10,len(rows))];chapters.append({'id':i+1,'start':group[0]['start'],'end':group[-1]['end'],'title':titles[i],'voice':' '.join(x['voice'] for x in group)})
dump(D/'CHAPTERS_14.json',chapters)
script=TITLE+'\n\n'+'\n\n'.join(f"{x['id']:03} | {stamp(x['start'])}–{stamp(x['end'])}\n{x['voice']}" for x in rows)+'\n'
(D/'KICH_BAN_EN_22m32s.txt').write_text(script,encoding='utf-8-sig')
(D/'en-US.txt').write_text('\n\n'.join(x['voice'] for x in rows)+'\n')
(D/'en-US.srt').write_text('\n\n'.join(f"{x['id']}\n{stamp(x['start'])} --> {stamp(x['end'])}\n{x['voice']}" for x in rows)+'\n')
for i in range(12):
 group=prompts[i*10:(i+1)*10];body='\n\n'.join(f"{p['id']:03}. {p['prompt']}" for p in group)+'\n'
 (P/f'LAND_BRIDGES_38_PROMPTS_{i+1:02}_{group[0]["id"]:03}_{group[-1]["id"]:03}.txt').write_text(body,encoding='utf-8-sig')
fields=['id','start','end','prompt_id','action','reuse_from_cue','use_seconds','voice','visual']
with (D/'TIMELINE_136_CANH.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
reuse=[x for x in rows if x['action']=='REUSE'];(D/'CAC_CANH_DUNG_LAI.txt').write_text('16 MỐC DÙNG LẠI — KHÔNG TẠO LẠI CLIP\n\n'+'\n'.join(f"Cue{x['id']:03} {stamp(x['start'])}–{stamp(x['end'])}: dùng clip{x['prompt_id']:03}.mp4, cùng bối cảnh cue{x['reuse_from_cue']:03}; lấy{x['use_seconds']}giây." for x in reuse)+'\n',encoding='utf-8-sig')
# A planned ten-shot hook, to be conformed to the actual supplied footage later.
hook_sources=[1,2,4,6,13,24,31,52,79,8];durations=[3,2.5,2.5,2,3,3,4,3,3,4];cursor=0;hook=[]
for sid,seconds in zip(hook_sources,durations):
 row=rows[sid-1];hook.append({'start':cursor,'end':cursor+seconds,'source_cue':sid,'prompt_id':row['prompt_id'],'note':'Planned source; confirm actual footage quality and first30second voice before final edit.'});cursor+=seconds
assert cursor==30 and len({x['prompt_id'] for x in hook})==10
dump(D/'OPENING_10_SHOTS_30s_PLANNED.json',hook)
for name in ['NGUON_KIEM_CHUNG.md','PHAN_TICH_VIDEO_NGUON.md']:shutil.copyfile(R/name,D/name)
baseline=json.loads((R/'BASELINE_VOICE_PROFILES.json').read_text());dump(D/'VOICE_PROFILES_LOCKED_BASELINE.json',baseline)
guide='''CHỦ ĐỀ38 —22:32—CẦU ĐẤT QUA NHỮNG CHU KỲ BĂNG HÀ

1. Kịch bản chính tiếng Anh: KICH_BAN_EN_22m32s.txt. Có136mốc lời:135×10giây+2giây=1.352giây. SRT sẽ khớp các mốc này khi voice đã được dựng/kiểm tra; hiện là kế hoạch.
2. Có120prompt mới,12TXT trong PROMPTS, đúng10prompt/TXT. Tạo120clip im lặng, mỗi clip10giây, đặt tên001.mp4…120.mp4 theo IDprompt, không đặt tên theo IDcue.
3. TIMELINE_136_CANH.csv nối IDcue với IDprompt.16mốc REUSE dùng lại clip đã có; không tạo lại. Xem CAC_CANH_DUNG_LAI.txt. Cue136dùng2giây từ clip001; không nối cả10giây vào cuối.
4. Không có trẻ em hoặc thiếu niên, kể cả tranh, nền, bóng và phản chiếu. Không có lời nói, nhạc hoặc audio stream. Nếu generator vẫn trả tiếng, tắt/xóa toàn bộ tiếng clip khi dựng.
5. Bản đồ chính xác, tên, số và tuyến phải kiểm tra rồi thêm trong phần mềm dựng. Các mô hình trong prompt chỉ minh họa nguyên lý. Không dùng AI để giả thành hồ sơ nghiên cứu thật.
6. Sau khi có footage: chọn10cảnh cho30giây đầu theo OPENING_10_SHOTS_30s_PLANNED.json. Phần này đã nằm trong22:32, không cộng thêm. Các nguồn đề xuất phải được duyệt lại khi có clip thật.
7. Tạo17voice riêng sau khi bàn giao tài liệu.16giọng nam dùng các voiceIDđã khóa; H'môngnữ dùng female-3 trong toolHmong1.6.6. Tất cả phải giải mã đúng64.896.000mẫu ở48kHz. Không chỉ so thời lượng hiển thị MP3.
8. Tiếng Anh bám136mốc; các bản dịch giữ14mốc chương với thời điểm0–100–200…1300–1352giây. Cùng tổng thời lượng không có nghĩa là từ hoặc câu từng nước trùng từng10giây.
9. Toolvà17profilegiữ nguyên nhận diện giọng; chỉ thời gian và nội dung thay đổi. Các bản dịch vẫn cần kiểm tra nghe bản ngữ, đặc biệt phương ngữ H'môngTrắng; không gọi bước kiểm kỹ thuật là chứng nhận bản ngữ.
10. Bộ này gồm kịch bản, prompt và hồ sơ chuẩn bị; không phải footage đã tạo hay MP4đã edit. Video hoàn chỉnh được dựng sau khi người dùng cung cấp clip.
'''
(D/'HUONG_DAN_SU_DUNG.txt').write_text(guide,encoding='utf-8-sig')
words=sum(len(re.findall(r"\b[\w'-]+\b",r['voice'])) for r in rows)
qa={'status':'passed','topic_id':38,'target_seconds':1352,'english_words':words,'planned_words_per_minute':round(words/(1352/60),1),'cues':136,'ten_second_cues':135,'final_cue_seconds':2,'unique_prompts':120,'reused_slots':16,'prompt_txt_files':12,'prompts_per_txt':10,'all_prompts_silent_suffix':all(p['prompt'].endswith('không có âm thanh') for p in prompts),'minor_exclusion_in_every_prompt':all('No children, infants, adolescents' in p['prompt'] for p in prompts),'english_srt_cues':136,'translated_chapters':14,'chapter_seconds':[c['end']-c['start'] for c in chapters],'expected_audio_frames_48000':64896000,'planned_video_frames_24fps':32448,'footage_generated':False,'video_edited':False,'voices_generated':False}
dump(D/'DOCUMENT_QA.json',qa)
def package():
 archive=R/'LAND_BRIDGES_38_TAI_LIEU_22m32s.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(D.rglob('*')):
   if p.is_file():z.write(p,p.relative_to(D))
 return archive
archive=package();print(json.dumps({**qa,'archive':str(archive),'archive_bytes':archive.stat().st_size}),flush=True)
