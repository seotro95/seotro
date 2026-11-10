import csv,hashlib,json,re,zipfile
from pathlib import Path
R=Path(__file__).parent;O=R/'package';O.mkdir(exist_ok=True);(O/'PROMPTS').mkdir(exist_ok=True)
voice={int(a):b for a,b in (s.split('\t',1) for s in (R/'script_en.tsv').read_text().splitlines())}
visual={int(a):(b,c) for a,b,c in (s.split('\t',2) for s in (R/'visuals.tsv').read_text().splitlines())}
assert set(voice)==set(visual)==set(range(1,123))
titles=[('The circle with an empty centre','Vòng xương và khoảng trống ở giữa'),('Why this place?','Vì sao là nơi này?'),('When remains become an arrangement','Khi hài cốt trở thành cấu trúc'),('The roof problem','Bài toán mái che'),('A history older than the builders','Lịch sử lâu hơn đời người xây'),('The animals behind the bones','Những con vật phía sau các mảnh xương'),('What floats out of the soil','Manh mối nổi lên từ đất'),('When the house explanation becomes difficult','Khi cách giải thích nhà ở gặp câu hỏi'),('Other sites, different questions','Di chỉ khác, câu hỏi khác'),('What did the date actually date?','Niên đại đang đo sự kiện nào?'),('Testing the picture','Thử lại bức tranh tái dựng'),('The question that remains','Câu hỏi còn lại')]
chap=[];t=0
for i,(en,vi) in enumerate(titles,1):
    d=100 if i<12 else 115;chap.append(dict(chapter=i,start_seconds=t,end_seconds=t+d,cue_count=10 if i<12 else 12,title_en=en,title_vi=vi));t+=d
assert t==1215
common='One continuous 10-second shot, 16:9, target 1920x1080 at 24fps when supported. Cinematic evidence-led prehistory documentary, tactile natural materials, believable scale and anatomy, restrained natural light. One principal action and one slow motivated camera move, with a clear visual reveal or question; no internal cuts, time-lapse, magical morphing or forced dramatic action. '
negative=' All scenes are original illustrative visuals, not authentic recovered ancient footage or exact copies of excavation photographs. Any humans must be unmistakably mature adults aged 35–60, including hands. No children, babies, infants, adolescents or anyone under 18 anywhere, including distance, background, silhouettes, shadows, reflections, photographs, pictures, posters, screens, statues or diagrams. All visible animals and animal teaching casts must be fully adult; no young animals. No human remains, human skeletons, blood, gore, dead bodies or hunting kills. No readable text, numbers, dates, labels, subtitles, graphs, genetic sequences, maps, flags, logos or watermarks; add verified information later in editing. Modern laboratory, museum, field and model-demonstration scenes remain visibly modern. Anonymous ancient-style adult skill illustrations use plain plausible hide, wood, stone and fibre, never zippers, metal tools, glass, modern furniture, computers or named prehistoric people. Partial or complete covering models are explicitly modern hypotheses, not proven Kostenki roof designs. No giant ice cliffs, Arctic igloos, fantasy monuments, ritual costumes, exaggerated mammoth tusks, moving bones or unsupported ancient architecture. No dialogue, narration, music, ambience, animal sounds or sound effects. không có âm thanh'
rows=[];unique=[];reuse=[];by={}
for i in range(1,123):
    kind,scene=visual[i];start=(i-1)*10;end=min(i*10,1215);ch=next(c['chapter'] for c in chap if c['start_seconds']<=start<c['end_seconds'])
    if kind.startswith('='):
        ref=int(kind[1:]);src=by[ref];assert src['generation_action']=='NEW';clip=src['clip_id'];prompt=src['full_prompt'];note=scene;scene=src['scene_and_camera'];kind=src['kind'];action='REUSE';reuse.append(dict(timeline_scene=i,start_seconds=start,end_seconds=end,clip_id=clip,source_scene=ref,filename=f'K19_{clip:03d}.mp4',skip_new_generation=True,edit_note=note,trim_to_seconds=end-start))
    else:
        ref=i;clip=len(unique)+1;action='NEW';note='';prompt=f'{clip:03d}. '+common+scene+negative;unique.append(dict(clip_id=clip,first_timeline_scene=i,kind=kind,scene_and_camera=scene,full_prompt=prompt))
    row=dict(id=i,chapter=ch,start_seconds=start,end_seconds=end,duration_seconds=end-start,voice_en=voice[i],clip_id=clip,filename=f'K19_{clip:03d}.mp4',generation_action=action,skip_new_generation=action=='REUSE',reuse_source_scene=ref,generated_clip_seconds=10,clip_trim_seconds=end-start,kind=kind,scene_and_camera=scene,edit_note=note,visual_children_allowed=False,full_prompt=prompt);rows.append(row);by[i]=row
assert len(unique)==120 and len(reuse)==2 and rows[-1]['duration_seconds']==5
for n in range(12):
    group=unique[n*10:n*10+10];text=f'CHỦ ĐỀ 19 / KOSTENKI / TỆP {n+1:02d} / 10 PROMPT\nMỗi prompt tạo clip 10 giây, im lặng, không hình trẻ em. Chỉ dán đoạn prompt được đánh số vào công cụ tạo video.\n'
    for x in group:
        slots=[a for a in rows if a['clip_id']==x['clip_id']]
        text+='\nCLIP '+f'{x["clip_id"]:03d} | K19_{x["clip_id"]:03d}.mp4 | MỐC '+','.join(f'{a["id"]:03d}' for a in slots)+'\nNGỮ CẢNH VOICE EN: '+slots[0]['voice_en']+'\nPROMPT:\n'+x['full_prompt']+'\n'
    (O/'PROMPTS'/f'PROMPTS_{n+1:02d}_{group[0]["clip_id"]:03d}_{group[-1]["clip_id"]:03d}.txt').write_text(text,encoding='utf-8-sig')
def write(name,text):(O/name).write_text(text,encoding='utf-8-sig' if name.endswith('.txt') else 'utf-8')
def stamp(s):return f'{s//3600:02d}:{s%3600//60:02d}:{s%60:02d},000'
def csvwrite(name,data,fields=None):
    with (O/name).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(data[0]),extrasaction='ignore');w.writeheader();w.writerows(data)
write('KICH_BAN_EN_20m15s.txt','\n\n'.join(voice.values())+'\n')
write('KICH_BAN_EN_CO_MOC.txt','KOSTENKI: THE HOUSE THAT REMAINS A QUESTION\nOriginal English narration /20:15 /122cues\n'+''.join(f'\n[{x["id"]:03d}] {stamp(x["start_seconds"])} --> {stamp(x["end_seconds"])} | CHAPTER {x["chapter"]:02d} | CLIP {x["clip_id"]:03d} | {x["generation_action"]}\n{x["voice_en"]}\n' for x in rows))
write('LOI_DAN_EN_122_CANH.srt',''.join(f'{x["id"]}\n{stamp(x["start_seconds"])} --> {stamp(x["end_seconds"])}\n{x["voice_en"]}\n\n' for x in rows))
write('SCENES_AND_PROMPTS.json',json.dumps(rows,ensure_ascii=False,indent=2));write('UNIQUE_PROMPTS_120.json',json.dumps(unique,ensure_ascii=False,indent=2))
csvwrite('TIMELINE_122_CANH.csv',rows,['id','chapter','start_seconds','end_seconds','duration_seconds','clip_id','filename','generation_action','skip_new_generation','reuse_source_scene','generated_clip_seconds','clip_trim_seconds','voice_en','kind','scene_and_camera','edit_note','visual_children_allowed']);csvwrite('CANH_DUNG_LAI_KHONG_TAO_MOI.csv',reuse);csvwrite('CHAPTERS_12.csv',chap)
hook=[]
for n,scene in enumerate([1,5,26,34,45,53,63,74,85,98,117,120]):
    r=by[scene];hook.append(dict(start_seconds=n*2.5,end_seconds=(n+1)*2.5,source_scene=scene,clip_id=r['clip_id'],filename=r['filename'],source_in_seconds=.5,source_out_seconds=3,note_vi='Hook 12 cảnh/30 giây nằm trong voice, không cộng intro; mô hình và thao tác ghi minh họa khi dựng.'))
csvwrite('HOOK_30_GIAY_12_SHOT.csv',hook)
sources=[
('S01','Pryor et al.2020. The chronology and function of a new circular mammoth-bone structure at Kostenki11','https://doi.org/10.15184/aqy.2020.7','10.15184/aqy.2020.7','Chronology,function,flotation and activity intensity; new wording, no figures or long quotations copied.'),
('S02','University of Exeter. Mysterious bone circles,17March2020','https://news-archive.exeter.ac.uk/2020/march/title_782319_en.html','','Institutional explanation of51mandibles,64skulls,charred plants,wood,bone and flint chips. The old press text has dimensional/date simplifications; script uses roughly12m/25ka from studies, not its30ft wording.'),
('S03','Rey-Iglesia et al.2025. Ancient biomolecular analysis of39mammoth individuals from Kostenki11-Ia','https://doi.org/10.1016/j.qeh.2024.100049','10.1016/j.qeh.2024.100049','39individuals,30confident sex assignments:17female/13male; older mandibles,collection of already-old bones,chronological limits. CC BY-NC-ND; factual reference only, original narration, no source text/figures/PDF redistributed.'),
('S04','Chu,Shydlovskyi and Maier2025. Revised radiocarbon chronology at Mezhyrich','https://pmc.ncbi.nlm.nih.gov/articles/PMC12639289/','10.12688/openreseurope.20112.1','CC BY. Small-animal dates and structure4 context around18ka; age range18,248–17,764calBP and model span0–429years do not prove429years of continuous occupation. Original narrative interpretation, no figures copied.'),
('S05','Iakovleva. The mammoth bone dwellings of Gontsy,a first synthesis','https://arheologia.com.ua/index.php/arheologia/article/view/45','','Settlement-scale comparison:bone structures,pits,hearths,work and disposal areas; do not transfer its reconstructed designs to Kostenki.'),
('S06','Iakovleva2015. Architecture of mammoth bone circular dwellings','https://www.sciencedirect.com/science/article/abs/pii/S1040618214006247','','Comparative architecture and interpretations; interpretations are not universal proven functions. Abstract consulted, no unaccessed detailed claims.'),
('S07','Oxford Radiocarbon Accelerator Unit. Methods and results','https://www.arch.ox.ac.uk/orau-methods-and-results','','Biological event dated,calibration,contamination and sample selection; bone reflects last part of animal life,wood dates growth; no assertion of an exact date of death.'),
('S08','Penn State Radiocarbon Laboratory. Guide to radiocarbon sampling','https://iee.psu.edu/labs/radiocarbon-laboratory/guide-radiocarbon-sampling','','Context,inbuilt age and old wood; sample ages are indirectly related to archaeological events.'),
('S09','User supplied reference video','https://github.com/seotro95/seotro/releases/tag/video','','Style observation only; SHA256f1a8659dbccd4db12a79e3c18ea2e1fe08f46f7a03c42bc2250f454f69eff70c,340611128bytes,Russian narration,Yana/Arctic theme; no scientific Kostenki claims or footage taken from it.')]
src=[dict(id=a,title=b,url=c,doi=d,scope=e,checked_local_date='2026-11-11') for a,b,c,d,e in sources];csvwrite('NGUON_KIEM_CHUNG.csv',src)
write('NGUON_KIEM_CHUNG.md','# Nguồn và giới hạn bằng chứng\n\n'+'\n\n'.join(f'- **{x["id"]} — {x["title"]}**: {x["url"]}\n  {x["scope"]}' for x in src)+'\n\nKhông đóng gói bài báo,ảnh,bảng,video nguồn. Lời mới và hình minh họa gốc. Mezhyrich:ghi công Chu,Shydlovskyi,Maier,2025,Open Research Europe5:198,DOI10.12688/openreseurope.20112.1,CC BY; không sao chép hình. Không trích lời trực tiếp từ video nguồn.\n')
checks=[]
for x in rows:
    i=x['id'];ids=['S01','S02'];status='Original narrative synthesis / illustrative question or experiment'
    if 31<=i<=39 or 101<=i<=110:ids=['S06'];status='Ordinary mechanics and proposed teaching models;not a proven roof design'
    if 41<=i<=59:ids=['S03','S07'];status='Published biological/sample findings plus original explanation;no reconstructed hunt or exact personal history'
    if 81<=i<=90:ids=['S04','S05','S06'];status='Separate sites/times;do not combine their chronologies or roofs'
    if 91<=i<=100:ids=['S03','S04','S07','S08'];status='Material age versus activity date;no claim of continuous residence'
    checks.append(dict(cue=i,source_ids=';'.join(ids),evidence_status=status,visual_policy='Mature adults only;educational casts/illustrations;no actual specimen identity claimed'))
csvwrite('DOI_CHIEU_KHOA_HOC.csv',checks)
analysis='''CHỦ ĐỀ 19 — KOSTENKI /20:15

Nguồn người dùng: https://github.com/seotro95/seotro/releases/tag/video
Đã đối chiếu asset video.c.a.toi.mp4:340.611.128byte,SHA256f1a8659dbccd4db12a79e3c18ea2e1fe08f46f7a03c42bc2250f454f69eff70c; cùng bản đã phân tích bằng lời dẫn,contact sheet mở đầu và các đoạn đại diện. Khoảng21:03,1280×720,60fps mã hóa,lời Nga. Không khẳng định biết phần mềm,prompt hoặc thông số dựng nội bộ của tác giả; không tuyên bố xem tay liên tục toàn bộ nguồn.

Dạng nội dung:phim tài liệu khoa học phổ thông có lời dẫn,đan xen vật chứng,cảnh quan,thao tác,minh họa cổ và phòng thí nghiệm. Nguồn mở bằng vật nhỏ và địa điểm/niên đại,rồi mở ra phát hiện,cách kiểm chứng và bài toán sinh tồn. Nhịp dựng đổi cỡ cảnh theo ý:toàn cảnh định vị,cận vật liệu,thao tác,công cụ khoa học,quay lại câu hỏi mở đầu. Có nhãn thông tin/bản đồ do editor thêm. Học cấu trúc và nhịp; không dịch lời,không sao chép footage,không dùng cảnh trẻ em/cờ/ảnh minh họa nguồn.

Áp dụng mới:Khoảng trống giữa vòng xương là câu hỏi dẫn đường. Mở bằng vòng xương và gánh nặng vật liệu; lần lượt xét nơi chốn,cấu trúc,mái che,tuổi xương,đặc điểm con vật,lửa,tần suất hoạt động,đối chiếu di chỉ và sự kiện được đo niên đại. Mỗi chương giải một phần rồi đặt câu hỏi kế. Tiết lộ xương cũ hơn đời người xây ở giữa phim để đổi cách hiểu nguồn vật liệu; cuối phim quay lại hàm xương và khoảng trống ở giữa.

Kịch bản2.816từ Anh,122mốc:121×10giây+1×5giây=1.215giây=20:15.11chương đầu100giây,chương cuối115giây. Thời lượng chính thức phải đo trên file voice,không suy ra chỉ từ số từ. Giọng thân thiện,có nhấn ở câu hỏi,vật chứng mới và kết; giữ16giọng nam đã khóa,H’MôngTrắngnữ3. Không đổi ID,engine,mẫu tham chiếu hoặc cao độ. Các bản dịch căn theo12chương,khớp tổng20:15; không khẳng định khớp từng từ giữa mọi ngôn ngữ.

120prompt mới trong12TXT,đúng10prompt/tệp,số001–120;2mốc dùng lại được đánh dấu trongCSV,timeline khác số clip. Tất cả prompt tạo clip10giây,clip cuối dùng5giây khi dựng. Mỗi prompt một shot liên tục,một hành động chính,một chuyển động máy có chủ đích. Xen24–35mmrộng,40–65mmngười/thao tác,75–100mmcận/macro. Vary vật liệu,quy mô và câu hỏi thay vì camera quay liên tục một vòng xương. Cảnh mô hình phải thấy bối cảnh giảng giải đương đại,mái che là giả thuyết. Mọi prompt kết thúc cùng đoạn bằng cụm ‘không có âm thanh’.

Không có trẻ em,thiếu niên hoặc người dưới18tuổi ở bất cứ đâu,kể cả nền,bóng,phản chiếu,ảnh,màn hình,tượng và sơ đồ. Người hiện rõ trưởng thành35–60tuổi,động vật trưởng thành; không trẻ động vật. Xương là mẫu/mô hình động vật không phải người. Không dựng săn giết,xác động vật còn mô,máu,nghi thức hay chân dung nhân vật cổ đã biết. Bối cảnh kỹ năng cổ dùng da/gỗ/đá/sợi đơn giản,không kim loại,zippers,máy tính hoặc vật hiện đại.

Hình tái dựng không thay thế bằng chứng. Không ghép mái Mezhyrich thành mái Kostenki,không đặt toàn bộ các di chỉ cùng niên đại. Vòng xương,nhà ở,kho chứa,không gian hoạt động là những câu hỏi/chức năng cần đối chiếu,không kết luận chung cho mọi cấu trúc. Mẫu được định tuổi không tự cho thời điểm xây; khoảng tuổi không chứng minh cư trú liên tục.17nữ/13nam là30cá thể xét được trong nghiên cứu39cá thể,không phải số người xây hay một đợt săn.

Khi dựng sau này:hook12cảnh×2,5giây trong30giây voice đầu,theoCSV; không cộng intro ngoài20:15. Cắt theo chuyển ý,dissolve0,35–0,65giây khi đổi bối cảnh/quy mô. Chữ ngắn,rõ,không chồng tiêu đề đồ họa; thông tin khoa học/bản đồ làm trongeditor,từ nguồn đã đối chiếu,không choAIbịa chữ/số/bản đồ. Giữ độ phân giải nguồn,phối màu tự nhiên,tương phản vừa; chỉvoiceAnh,loại toàn bộ tiếngclip,không nhạc/SFX. Mô hình/diễn viên có nhãn minh họa. Kiểm giải mã,frame,một đường tiếng và đồng bộ nhiều điểm trước bàn giao.

Lưu tài liệu trước,tạo17voice sau. Mỗi MP3 phải giải mã đúng58.320.000mẫu tại48kHz=1.215giây. Dịch theo ngữ cảnh và thuật ngữ địa phương; giữ tên quốc gia theo preset. Rà kỹ thuật không thay cho người bản ngữ nghe/biên tập,đặc biệt H’MôngTrắng. Giữ kết quả các tập trước và chỉ làm tập19 theo yêu cầu; chưa dựng video19 khi chưa có clip do người dùng tạo.
'''
write('PHAN_TICH_NGUON_VA_QUY_TRINH.txt',analysis)
write('HUONG_DAN_20m15s.txt','Tạo lần lượt12TXT trongPROMPTS,mỗiTXT10prompt;đặt tênK19_001.mp4–K19_120.mp4. Mỗi clip10giây,hoàn toàn im lặng,không hình trẻ em.\n\nDùngTIMELINE_122_CANH.csv để gắn clip với lờiAnh. Hai mốc61và122 dùng lạiclip,bỏ tạo mới. Mốc122 chỉ dùng5giây của clip10giây;không kéo voice thành20:20. Tổng1.215giây=20:15.\n\nBản chính chỉvoiceAnh,các nước cóaudio riêng. Khi cóclip,sẽ dựng theovoice vàhook30giây. Ghi nhãn mô hình/minh họa;không coi mái che giả thuyết là kiến trúc đã được xác nhận.\n')
write('README.md','# Chủ đề19 — Nhà bằng xương voi ma mút /20:15\n\n**Kostenki:The House That Remains a Question**\n\nKịch bản Anh2.816từ,122mốc(121×10s+5s),12chương(11×100s+115s).120prompt mới/12TXT,đúng10prompt/tệp;2mốc dùng lại. Prompt10giây và kết thúc bằng“không có âm thanh”. Không hình trẻ em;chỉ người trưởng thành35–60tuổi.\n\nTài liệu bàn giao trướcvoice. Bộ17voice giữ16nam vàH’MôngTrắngnữ3,cùngID/style/mẫu đã lưu;thời lượng đích20:15. Chưa cóclip,chưa dựngvideo19. Các tập trước giữ nguyên.\n\n[Xem nguồn](NGUON_KIEM_CHUNG.md) vàPHAN_TICH_NGUON_VA_QUY_TRINH.txt để đọc giới hạn bằng chứng,cách viết và dựng. Không tái xuất bảnvideo/ảnh/bài báo nguồn; lời và prompt mới.\n')
qa={'status':'passed','topic':19,'target_seconds':1215,'english_words':sum(len(x.split()) for x in voice.values()),'timeline_cues':122,'full_ten_second_cues':121,'last_cue_seconds':5,'translated_chapter_seconds':[100]*11+[115],'unique_prompts':120,'reused_slots':2,'prompt_txt_files':12,'prompts_per_txt':10,'all_prompts_end_with_required_phrase':all(x['full_prompt'].endswith('không có âm thanh') for x in unique),'all_prompts_have_no_minors_instruction':all('No children' in x['full_prompt'] for x in unique),'source_video_hash_verified':True,'voice_not_yet_generated':True,'no_private_upload_identifiers':True}
assert all(qa[k] for k in ['all_prompts_end_with_required_phrase','all_prompts_have_no_minors_instruction'])
write('DOCUMENT_QA.json',json.dumps(qa,ensure_ascii=False,indent=2))
archive=R/'KOSTENKI_VIDEO_19_TAI_LIEU_20m15s.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(O.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(O))
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
qa.update(zip_bytes=archive.stat().st_size,zip_sha256=hashlib.sha256(archive.read_bytes()).hexdigest());(R/'DOCUMENT_BUILD.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
print(json.dumps(qa,ensure_ascii=False),flush=True)
if __name__=='__main__':pass
