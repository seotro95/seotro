import csv,hashlib,json,re,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';P=D/'PROMPTS';V=R/'voice/scripts'
for p in [D,P,V]:p.mkdir(parents=True,exist_ok=True)
TARGET=1358;FRAMES=TARGET*48000;PREFIX='NEANDERTHAL_FIRE_71';TITLE='The Missing Fires of the Neanderthals';TAG='neanderthal-fire-video-71-22m38s'
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
        setting='A generic illustrative prehistoric setting, natural landscape, contemporary research scene or clearly manufactured teaching model as specified. Prehistoric human figures are respectful plausible Neanderthal-era reconstructions, never authenticated portraits or a named individual. Barnham scenes do not identify a known fire-maker. Reconstructed hearths, tool wear, soil profiles and layouts are explanatory examples, never actual recovered artifacts, measured micrographs, surveyed site plans or scientific data.'
        prompt=f'Create one continuous moving 10-second shot, 16:9, photorealistic science-documentary cinematography. {visual} {setting} Use one main action and one deliberate camera movement, realistic materials, anatomy, scale, light and shadows; no cuts, transformations or time-lapse. Every person, including visible hands, must be unmistakably mature, aged 35–65. Prehistoric adults wear practical fully covering clothing; modern researchers wear contemporary clothing. No children, infants, adolescents, minors, child-sized or child-like figures anywhere, including backgrounds, silhouettes, shadows, reflections, photos, artwork, screens and model figures. No juvenile animals, human remains, skulls, blood, gore, hunting, attacks, injuries, suffering or dangerous contact with flame. Fire demonstrations are small and contained; no large spreading fire, explosive ignition or engulfing smoke. No pottery, metal tools or modern objects in prehistoric scenes. No readable text, captions, letters, dates, numbers, logos, flags, watermarks, diagnostic labels, false chemical results, measured data or readable displays. No speech, dialogue, narration, singing, lip-sync, music, sound effects or audio stream. Video không có lời nói và không có âm thanh'
        prompts.append({'id':pid,'source_cue':sid,'voice_context':voice,'visual':visual,'prompt':prompt})
    rows.append({'id':sid,'start':start,'end':end,'voice':voice,'visual':visual,'prompt_id':pid,'action':action,'reuse_from_cue':source,'use_seconds':end-start})
assert len(rows)==136 and len(prompts)==130 and sum(x['action']=='REUSE' for x in rows)==6
assert rows[-1]['end']==TARGET and rows[-1]['use_seconds']==8
assert all(a['end']==b['start'] for a,b in zip(rows,rows[1:]))
dump(D/'SCENES_AND_PROMPTS.json',rows);dump(D/'ALL_PROMPTS.json',prompts);dump(V/'en-US.json',rows)
titles=['The ember and the missing flame','Four different fire questions','What a fire leaves behind','The French cold-period puzzle','The second life of a hearth','The choices behind a flame','El Salt and repeated returns','The fire-making tool argument','Chemical signals at Lusakert','The Barnham discovery','Fire and living space at Abric Romani','Knowledge, variation and the limits of a model','The ember we return to']
chapters=[]
for i in range(13):
    group=rows[i*11:min((i+1)*11,len(rows))]
    chapters.append({'id':i+1,'start':group[0]['start'],'end':group[-1]['end'],'title':titles[i],'voice':' '.join(x['voice'] for x in group)})
assert [c['end']-c['start'] for c in chapters]==[110]*12+[38]
dump(D/'CHAPTERS_13.json',chapters)
script=TITLE+'\n\n'+'\n\n'.join(f"{x['id']:03} | {stamp(x['start'])}–{stamp(x['end'])}\n{x['voice']}" for x in rows)+'\n'
(D/'KICH_BAN_EN_22m38s.txt').write_text(script,encoding='utf-8-sig')
(D/'en-US.txt').write_text('\n\n'.join(x['voice'] for x in rows)+'\n')
(D/'en-US.srt').write_text('\n\n'.join(f"{x['id']}\n{stamp(x['start'])} --> {stamp(x['end'])}\n{x['voice']}" for x in rows)+'\n')
for i in range(13):
    group=prompts[i*10:(i+1)*10]
    (P/f'{PREFIX}_PROMPTS_{i+1:02}_{group[0]["id"]:03}_{group[-1]["id"]:03}.txt').write_text('\n\n'.join(f"{x['id']:03}. {x['prompt']}" for x in group)+'\n',encoding='utf-8-sig')
with (D/'TIMELINE_136_CANH.csv').open('w',newline='',encoding='utf-8-sig') as f:
    fields=['id','start','end','prompt_id','action','reuse_from_cue','use_seconds','voice','visual']
    writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(rows)
reuse=[x for x in rows if x['action']=='REUSE']
(D/'CAC_CANH_DUNG_LAI.txt').write_text('6 MỐC DÙNG LẠI — KHÔNG TẠO LẠI CLIP\n\n'+'\n'.join(f"Mốc {x['id']:03} {stamp(x['start'])}–{stamp(x['end'])}: dùng clip {x['prompt_id']:03}.mp4, bối cảnh của mốc {x['reuse_from_cue']:03}; lấy {x['use_seconds']} giây." for x in reuse)+'\n',encoding='utf-8-sig')
hook_sources=[1,2,4,5,6,8,13,26,44,7];durations=[3,3,3,3,2,3,3,3,3,4];cursor=0;hook=[]
for sid,t in zip(hook_sources,durations):
    row=rows[sid-1];hook.append({'start':cursor,'end':cursor+t,'source_cue':sid,'prompt_id':row['prompt_id'],'note':'Planned only; choose actual footage to match first30seconds of English narration. No attack or hunt reenactment.'});cursor+=t
assert cursor==30 and len({x['prompt_id'] for x in hook})==10
dump(D/'OPENING_10_SHOTS_30s_PLANNED.json',hook)
for n in ['NGUON_KIEM_CHUNG.md','PHAN_TICH_VIDEO_NGUON.md','VOICE_PROFILES_LOCKED_BASELINE.json','NAM_MINH_VOICE_LOCK.json','TOPICS_001_100_FROM_GITHUB.csv','5_TIEU_DE_VA_THUMBNAIL.txt']:
    shutil.copyfile(R/n,D/n)
guide='CHỦ ĐỀ 71 — NGƯỜI NEANDERTHAL VÀ LỬA — 22:38\n\n1. Kịch bản Anh có 136 mốc: 135 mốc 10 giây và mốc cuối 8 giây. Audio mục tiêu 1.358 giây, tương ứng 65.184.000 mẫu mono 48 kHz.\n2. Tạo 130 clip im lặng 10 giây từ 13 TXT trong PROMPTS, đúng 10 prompt/TXT. Đặt tên 001.mp4 đến 130.mp4 theo ID prompt, không theo ID mốc lời.\n3. TIMELINE_136_CANH.csv nối lời với clip; 6 mốc REUSE ghi rõ trong CAC_CANH_DUNG_LAI.txt. Mốc cuối dùng 8 giây từ clip 001.\n4. Mọi prompt cấm trẻ em và thiếu niên, cả ảnh, nền, màn hình, bóng và hình mô hình. Không lời nói, khẩu hình, nhạc, SFX hoặc audio stream. Xóa tiếng clip nếu công cụ vẫn tự tạo âm thanh.\n5. Công cụ, bếp, trầm tích và nhân vật là minh họa, không ảnh dữ liệu thật hay khuôn mặt xác thực. Không chữ, số liệu giả, di cốt người, máu, săn đuổi hoặc tấn công. Lửa nhỏ và được chứa trong khu vực minh họa; không cháy lan hoặc tiếp xúc nguy hiểm.\n6. Khi có footage, chọn 10 cảnh mạnh trong 30 giây đầu theo lời thực tế. Intro nằm trong 22:38. Phim chính chỉ voice Anh, không nhạc/SFX; thiếu cảnh dùng video chuyển động liên quan, không ảnh đứng hoặc thẻ chữ.\n7. Giữ 16 nhận diện khác từ tập 58. Riêng Việt đổi sang Nam Minh, ID thật vi-VN-NamMinhNeural, nam, locale vi-VN đã kiểm. Tổng 16 nam; H’mông female-3 nữ dùng công cụ riêng 1.6.6. Không đổi nhãn Adam thành Nam Minh hoặc sửa audio các tập cũ.\n8. Anh căn 136 mốc; bản dịch căn 13 chương chung: 12 chương 110 giây và 38 giây cuối. Cùng tổng thời lượng không có nghĩa từng từ giữa các ngôn ngữ đồng thời.\n9. SRT hiện là kế hoạch theo lời. SRT dịch theo chương cần chia nhỏ trước khi hiển thị. Chỉ bàn giao voice sau khi tạo đủ lời và giải mã từng tệp đúng 65.184.000 mẫu ở 48 kHz.\n10. Gói tài liệu giai đoạn này chưa chứa audio, footage hoặc MP4. Kiểm kỹ thuật không thay thế nghe/biên tập bản ngữ; phương ngữ H’mông Trắng chưa được kiểm độc lập.\n'
(D/'HUONG_DAN_SU_DUNG.txt').write_text(guide,encoding='utf-8-sig')
words=sum(len(re.findall(r"\b[\w'-]+\b",x['voice'])) for x in rows)
qa={'status':'passed','topic_id':71,'target_seconds':TARGET,'english_words':words,'planned_words_per_minute':round(words/(TARGET/60),1),'cues':136,'ten_second_cues':135,'final_cue_seconds':8,'unique_prompts':130,'reused_slots':6,'prompt_txt_files':13,'prompts_per_txt':10,'all_prompts_silent_suffix':all(x['prompt'].endswith('Video không có lời nói và không có âm thanh') for x in prompts),'minor_exclusion_in_every_prompt':all('No children, infants, adolescents, minors' in x['prompt'] for x in prompts),'translated_chapters':13,'chapter_seconds':[110]*12+[38],'expected_audio_frames_48000':FRAMES,'planned_video_frames_24fps':TARGET*24,'vietnamese_voice_id':'vi-VN-NamMinhNeural','native_voices_expected':1,'online_voices_expected':16,'voices_generated':False,'footage_generated':False,'video_edited':False}
dump(D/'DOCUMENT_QA.json',qa)
readme=f'# Chủ đề 71 — Người Neanderthal và hồ sơ lửa — 22:38\n\n[Tải bộ tài liệu]({BASE}{PREFIX}_TAI_LIEU_22m38s.zip) · [Kịch bản Anh TXT]({BASE}KICH_BAN_EN_22m38s.txt) · [5 tiêu đề và 5 prompt thumbnail]({BASE}5_TIEU_DE_VA_THUMBNAIL.txt)\n\n**The Missing Fires of the Neanderthals** có 3.500 từ Anh, 136 mốc, tổng 1.358 giây. Có 130 prompt mới trong 13 TXT, đúng 10 prompt/TXT, và 6 mốc dùng lại. Mọi clip mới dài 10 giây; mốc cuối dùng 8 giây. Mỗi prompt cấm trẻ em, thiếu niên và mọi lời nói/âm thanh.\n\nCâu chuyện tách bốn câu hỏi: có cháy, kiểm soát lửa, tạo lửa và dùng thường xuyên. Đi qua dấu nhiệt, trầm tích, chuỗi Pháp, El Salt, vết mòn công cụ, Lusakert, Barnham và Abric Romaní, phân biệt quan sát, diễn giải và mô hình. Cập nhật công bố Barnham cuối 2025 và nghiên cứu không gian Abric Romaní năm 2026; không biến một trường hợp thành kỹ năng hoặc thói quen của mọi nhóm người.\n\nĐây là bước bàn giao tài liệu trước khi tạo 17 voice. Theo yêu cầu mới, bản Việt dùng đúng **Nam Minh — vi-VN-NamMinhNeural**, nam, qua backend Melo 1.3.1. Các tập 45/58 giữ Adam của chúng; 16 nhận diện khác không đổi, H’mông female-3 nữ dùng công cụ riêng 1.6.6. Anh sẽ căn 136 mốc, bản dịch 13 chương chung: 12×110 giây và 38 giây cuối. Mỗi voice phải giải mã đúng 65.184.000 mẫu ở 48 kHz trước khi công bố.\n\nChưa có footage hoặc MP4 tập 71. Kế hoạch mở đầu 10 cảnh trong 30 giây nằm trong 22:38; phim chính chỉ voice Anh. Chưa có kiểm nghe/biên tập bản ngữ hoặc xác nhận độc lập phương ngữ H’mông Trắng.\n'
(D/'README.md').write_text(readme)
archive=R/f'{PREFIX}_TAI_LIEU_22m38s.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(D.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(D))
print(json.dumps({**qa,'archive_bytes':archive.stat().st_size}),flush=True)
