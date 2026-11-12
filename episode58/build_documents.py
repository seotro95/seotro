import csv,hashlib,json,re,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';P=D/'PROMPTS';V=R/'voice/scripts'
for p in [D,P,V]:p.mkdir(parents=True,exist_ok=True)
TARGET=1362;FRAMES=TARGET*48000;PREFIX='BONE_TRACES_58';TITLE='Before You Call It a Hunt';TAG='bone-traces-video-58-22m42s'
BASE=f'https://github.com/seotro95/seotro/releases/download/{TAG}/'
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def stamp(t):return f'{t//3600:02}:{t%3600//60:02}:{t%60:02},000'
rows=[];prompts=[]
for line in (R/'SCENES_DRAFT.tsv').read_text().splitlines():
    ident,voice,visual=line.split('|',2);sid=int(ident);assert sid==len(rows)+1
    start=(sid-1)*10;end=min(start+10,TARGET)
    if visual.startswith('REUSE:'):
        source=int(visual.split(':')[1]);assert source<sid
        earlier=rows[source-1];pid=earlier['prompt_id'];visual=earlier['visual'];action='REUSE'
    else:
        source=None;pid=len(prompts)+1;action='CREATE'
        setting='Contemporary research, a clearly manufactured teaching model or a generic natural landscape as specified. Wildlife shots show calm mature animals from a safe distant viewpoint; all specimens are clean adult-animal material or explicit resin replicas. This is an illustrative reconstruction, never an authenticated archaeological specimen, measured micrograph, dataset, excavation plan or record of a specific ancient encounter.'
        prompt=f'Create one continuous moving 10-second shot, 16:9, photorealistic science-documentary cinematography. {visual} {setting} Use one main action and one deliberate camera movement, physically realistic scale, contact, shadows and materials; no cuts or sudden transformations. Any person, including visible hands, must be unmistakably mature, aged 35–65, in appropriate contemporary research clothing. No children, infants, adolescents, minors, child-sized or child-like figures anywhere, including backgrounds, silhouettes, reflections, shadows, photos, artwork, model figures and screens. No juvenile animals. No human bones, human remains, blood, gore, carcasses, tissue, butchery, predation, attacks, hunting, injuries, suffering or threatening human-animal contact. Show separate clean specimens and inert teaching models instead of reenacting biological damage. No readable text, letters, captions, dates, numbers, logos, flags, watermarks, diagnostic labels, supposed measured data or readable computer displays. Do not portray generated grooves or casts as actual study findings. No speech, dialogue, narration, singing, lip-sync, music, sound effects or audio stream. Video không có lời nói và không có âm thanh'
        prompts.append({'id':pid,'source_cue':sid,'voice_context':voice,'visual':visual,'prompt':prompt})
    rows.append({'id':sid,'start':start,'end':end,'voice':voice,'visual':visual,'prompt_id':pid,'action':action,'reuse_from_cue':source,'use_seconds':end-start})
assert len(rows)==137 and len(prompts)==130 and sum(x['action']=='REUSE' for x in rows)==7
assert rows[-1]['end']==TARGET and rows[-1]['use_seconds']==2
assert all(a['end']==b['start'] for a,b in zip(rows,rows[1:]))
dump(D/'SCENES_AND_PROMPTS.json',rows);dump(D/'ALL_PROMPTS.json',prompts);dump(V/'en-US.json',rows)
titles=['The mark before the story','Describe before naming','The first suspects have teeth','The crocodile comparison','When the ground makes a line','Claws, gnawing and surface history','Making the case for a stone edge','Dikika and the weight of a claim','Who came first?','A processed animal is not yet a hunt','Testing eyes, microscopes and computers','Three trays and three different questions','Read the bone first']
chapters=[]
for i in range(13):
    group=rows[i*11:min((i+1)*11,len(rows))]
    chapters.append({'id':i+1,'start':group[0]['start'],'end':group[-1]['end'],'title':titles[i],'voice':' '.join(x['voice'] for x in group)})
assert [c['end']-c['start'] for c in chapters]==[110]*12+[42]
dump(D/'CHAPTERS_13.json',chapters)
script=TITLE+'\n\n'+'\n\n'.join(f"{x['id']:03} | {stamp(x['start'])}–{stamp(x['end'])}\n{x['voice']}" for x in rows)+'\n'
(D/'KICH_BAN_EN_22m42s.txt').write_text(script,encoding='utf-8-sig')
(D/'en-US.txt').write_text('\n\n'.join(x['voice'] for x in rows)+'\n')
(D/'en-US.srt').write_text('\n\n'.join(f"{x['id']}\n{stamp(x['start'])} --> {stamp(x['end'])}\n{x['voice']}" for x in rows)+'\n')
for i in range(13):
    group=prompts[i*10:(i+1)*10]
    (P/f'{PREFIX}_PROMPTS_{i+1:02}_{group[0]["id"]:03}_{group[-1]["id"]:03}.txt').write_text('\n\n'.join(f"{x['id']:03}. {x['prompt']}" for x in group)+'\n',encoding='utf-8-sig')
with (D/'TIMELINE_137_CANH.csv').open('w',newline='',encoding='utf-8-sig') as f:
    fields=['id','start','end','prompt_id','action','reuse_from_cue','use_seconds','voice','visual']
    writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(rows)
reuse=[x for x in rows if x['action']=='REUSE']
(D/'CAC_CANH_DUNG_LAI.txt').write_text('7 MỐC DÙNG LẠI — KHÔNG TẠO LẠI CLIP\n\n'+'\n'.join(f"Mốc {x['id']:03} {stamp(x['start'])}–{stamp(x['end'])}: dùng clip {x['prompt_id']:03}.mp4, bối cảnh của mốc {x['reuse_from_cue']:03}; lấy {x['use_seconds']} giây." for x in reuse)+'\n',encoding='utf-8-sig')
hook_sources=[1,2,3,5,7,18,30,31,43,6];durations=[3,3,3,3,2,3,3,3,3,4];cursor=0;hook=[]
for sid,t in zip(hook_sources,durations):
    row=rows[sid-1];hook.append({'start':cursor,'end':cursor+t,'source_cue':sid,'prompt_id':row['prompt_id'],'note':'Planned only; choose actual footage to match first30seconds of English narration. No attack or hunt reenactment.'});cursor+=t
assert cursor==30 and len({x['prompt_id'] for x in hook})==10
dump(D/'OPENING_10_SHOTS_30s_PLANNED.json',hook)
for n in ['NGUON_KIEM_CHUNG.md','PHAN_TICH_VIDEO_NGUON.md','VOICE_PROFILES_LOCKED_BASELINE.json','ADAM_VOICE_LOCK.json','TOPICS_001_100_FROM_GITHUB.csv','5_TIEU_DE_VA_THUMBNAIL.txt']:
    shutil.copyfile(R/n,D/n)
guide='''CHỦ ĐỀ 58 — MÓNG, RĂNG VÀ XƯƠNG — 22:42

1. Kịch bản Anh có 137 mốc: 136 mốc 10 giây và mốc cuối 2 giây. Thời lượng audio mục tiêu là 1.362 giây, tương ứng 65.376.000 mẫu mono 48 kHz.
2. Tạo 130 clip chuyển động im lặng 10 giây từ 13 TXT trong PROMPTS, đúng 10 prompt/TXT. Đặt tên 001.mp4 đến 130.mp4 theo ID prompt, không theo ID mốc lời.
3. TIMELINE_137_CANH.csv nối lời với clip; 7 mốc REUSE ghi rõ trong CAC_CANH_DUNG_LAI.txt. Mốc cuối dùng 2 giây từ clip 001.
4. Mọi prompt cấm trẻ em và thiếu niên, cả nền, phản chiếu, ảnh, màn hình và hình mô hình. Không lời nói, khẩu hình, nhạc, SFX hoặc audio stream. Xóa âm thanh clip nếu công cụ vẫn tự tạo ra tiếng.
5. Mọi mẫu vật minh họa là động vật trưởng thành sạch hoặc bản sao nhựa. Không di cốt người, máu, mô, giết mổ, săn đuổi, tấn công hoặc động vật bị thương. Mô hình minh họa không được dùng như ảnh đo thật, ảnh hóa thạch thật hay dữ liệu nghiên cứu.
6. Khi có footage, chọn 10 cảnh mạnh trong 30 giây đầu theo bản kế hoạch và chất lượng thực tế. Intro nằm trong tổng 22:42. Phim chính chỉ voice Anh, không nhạc/SFX. Cảnh thiếu dùng video chuyển động liên quan, không ảnh đứng hoặc thẻ chữ.
7. Giữ 17 nhận diện đã lưu ở tập 45: 16 nam, riêng H’mông female-3 nữ. Việt dùng đúng Adam native, nam miền Nam, qua Melo + Việt 1.3.1 / VieNeu 3.8.3; H’mông dùng công cụ riêng 1.6.6.
8. Bản Anh căn 137 mốc; bản dịch giữ 13 chương chung: 12 chương 110 giây và chương cuối 42 giây. Cùng thời lượng không có nghĩa từng từ giữa các ngôn ngữ đồng thời.
9. SRT hiện là kế hoạch theo lời. Các SRT dịch theo chương cần chia nhỏ trước khi hiển thị. Chỉ bàn giao audio sau khi tạo đủ lời và giải mã kiểm từng tệp đúng 65.376.000 mẫu.
10. Gói tài liệu ở giai đoạn này chưa có audio, footage hoặc MP4. Dịch/nghe bản ngữ độc lập và phương ngữ H’mông Trắng chưa được xác nhận.
'''
(D/'HUONG_DAN_SU_DUNG.txt').write_text(guide,encoding='utf-8-sig')
words=sum(len(re.findall(r"\b[\w'-]+\b",x['voice'])) for x in rows)
qa={'status':'passed','topic_id':58,'target_seconds':TARGET,'english_words':words,'planned_words_per_minute':round(words/(TARGET/60),1),'cues':137,'ten_second_cues':136,'final_cue_seconds':2,'unique_prompts':130,'reused_slots':7,'prompt_txt_files':13,'prompts_per_txt':10,'all_prompts_silent_suffix':all(x['prompt'].endswith('Video không có lời nói và không có âm thanh') for x in prompts),'minor_exclusion_in_every_prompt':all('No children, infants, adolescents, minors' in x['prompt'] for x in prompts),'translated_chapters':13,'chapter_seconds':[110]*12+[42],'expected_audio_frames_48000':FRAMES,'planned_video_frames_24fps':TARGET*24,'vietnamese_voice_id':'Adam','native_voices_expected':2,'online_voices_expected':15,'voices_generated':False,'footage_generated':False,'video_edited':False}
dump(D/'DOCUMENT_QA.json',qa)
readme=f'''# Chủ đề 58 — Móng, răng và xương — 22:42

[Tải kịch bản và prompt]({BASE}{PREFIX}_TAI_LIEU_22m42s.zip) · [Kịch bản Anh TXT]({BASE}KICH_BAN_EN_22m42s.txt) · [5 tiêu đề và 5 prompt thumbnail]({BASE}5_TIEU_DE_VA_THUMBNAIL.txt)

**Before You Call It a Hunt** có {words:,} từ Anh, 137 mốc và tổng 1.362 giây. Có 130 prompt mới trong 13 TXT, đúng 10 prompt/TXT, và 7 mốc dùng lại được đánh dấu. Mỗi clip mới dài 10 giây; mốc cuối chỉ dùng 2 giây. Mọi prompt không có trẻ em, thiếu niên, lời nói hoặc âm thanh.

Nội dung đi từ một rãnh nhỏ trên bản sao xương động vật qua dấu răng, cá sấu, giẫm đạp, móng, gặm, phong hóa và công cụ, đến tranh luận Dikika, thứ tự tiếp cận thức ăn và các phép kiểm bằng kính hiển vi. Ba khay cuối là tình huống giảng giải được nói rõ, không phải phát hiện mới. Phân biệt tác nhân gây dấu, thứ tự tác động và cách kiếm con vật; không dựng một cuộc săn chưa được chứng minh.

Đây là bước bàn giao tài liệu trước khi tạo 17 voice. Bản Việt giữ đúng Adam native, nam miền Nam, qua Melo + Việt 1.3.1; H’mông nữ dùng công cụ riêng 1.6.6 với reference female-3. Các nhận diện khác giữ như tập45. Bản Anh sẽ căn 137 mốc; bản dịch căn 13 chương chung. Mỗi voice phải giải mã đúng {FRAMES:,} mẫu ở 48 kHz, tương đương 22:42, trước khi phát hành.

Chưa có footage hoặc MP4 tập58. Kế hoạch mở đầu 10 cảnh trong 30 giây nằm trong tổng 22:42; phim chính chỉ voice Anh. Kiểm kỹ thuật không thay thế nghe/biên tập bản ngữ; phương ngữ H’mông Trắng chưa được kiểm độc lập.
'''
(D/'README.md').write_text(readme)
archive=R/f'{PREFIX}_TAI_LIEU_22m42s.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(D.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(D))
print(json.dumps({**qa,'archive_bytes':archive.stat().st_size}),flush=True)
