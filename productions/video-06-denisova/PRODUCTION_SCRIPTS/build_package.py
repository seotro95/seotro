import csv,hashlib,json,re,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;O=R/'package';O.mkdir(exist_ok=True);(O/'PROMPTS').mkdir(exist_ok=True)
voice={int(a):b for a,b in [l.split('\t',1) for l in (R/'script_en.tsv').read_text().splitlines()]};visual={int(a):(b,c) for a,b,c in [l.split('\t',2) for l in (R/'visuals.tsv').read_text().splitlines()]}
assert set(voice)==set(visual)==set(range(1,127))
titles=[('The fragment and the question','Mảnh xương và câu hỏi nhận diện'),('A cave is a layered archive','Hang động là hồ sơ nhiều lớp'),('Testing damaged molecular clues','Kiểm tra dấu vết phân tử đã hư hại'),('Two reports changed the comparison','Hai báo cáo thay đổi phép so sánh'),('What high coverage actually means','Độ bao phủ cao thực sự có nghĩa gì'),('Inherited traces in living people','Dấu vết được thừa hưởng ở người ngày nay'),('Proteins and the plateau connection','Protein và mối liên hệ với cao nguyên'),('The record beneath our feet','Hồ sơ bên dưới chân chúng ta'),('Meetings and diverse population histories','Gặp gỡ và lịch sử quần thể đa dạng'),('New fossil connections in2025','Những mối liên hệ hóa thạch năm2025'),('More fragments, wider questions in2026','Thêm mảnh xương, thêm câu hỏi năm2026'),('Return to the small surviving clue','Trở lại dấu vết nhỏ còn sót lại')]
chap=[];start=0
for n,((en,vi),count) in enumerate(zip(titles,[11]*6+[10]*6),1):chap.append(dict(chapter=n,start_seconds=start,end_seconds=start+count*10,cue_count=count,title_en=en,title_vi=vi));start+=count*10
assert start==1260
common='One continuous 10-second shot, 16:9, target 1920x1080, 24fps when supported. Restrained cinematic science documentary, one main action and one slow controlled camera move, stable object identity, plausible materials and mature adult anatomy. '
negative=' Silent video: no audio track, narration, speech, dialogue, music, ambience or sound effects. No children, babies, infants, adolescents or anyone under 18 anywhere, including background people, distant small figures, silhouettes, reflections, photographs, illustrations, statues, diagrams or screens. Every visible person must be unmistakably a mature adult aged 25-60. Never depict or reconstruct the young owners of Denisova3 or Denisova11; do not substitute an adult actor as their identified likeness. Bone-shaped replicas are generic isolated teaching objects, not photographs of actual recovered specimens; no attached anatomical body or depiction of a specimen owner. Any visible hands must belong only to unmistakably mature adult demonstrators; never reconstruct young anatomy or a juvenile likeness. An adult dental or mandibular teaching replica must have unmistakably mature permanent-tooth anatomy and no attached face or body. No generated text, letters, numbers, subtitles, dates, country flags, logos, broadcaster marks or watermarks. No invented measured genomes, numerical ancestry charts, exact genealogies, ethnic boundaries or proven migration routes. No glowing DNA inside fossils. Modern laboratories and fieldwork remain clearly modern. Any prehistoric practical-skill scene uses only anonymous mature adult reenactors, plausible stone, bone, wood, hide and fibre; no modern pens, notebooks, magnifiers, solar panels, computers, zippers, metal tools, igloos or claimed original prehistoric footage. No claimed exact Denisovan face, costume or cultural identity. Add verified labels and caveats during editing. Reference plates must remain geometrically unchanged; if generation cannot preserve them, animate the supplied PNG directly in editing instead.'
rows=[];unique=[];reuse=[];byid={}
for i in range(1,127):
 kind,v=visual[i];chapter=next(c['chapter'] for c in chap if c['start_seconds']<i*10<=c['end_seconds'])
 if kind.startswith('='):
  ref=int(kind[1:]);src=byid[ref];assert src['generation_action']=='NEW';clip=src['clip_id'];action='REUSE';full=src['full_prompt'];scene=src['scene_and_camera'];kind=src['kind'];note=v
  reuse.append(dict(timeline_scene=i,start_seconds=(i-1)*10,end_seconds=i*10,reuse_source_scene=ref,clip_id=clip,filename=f'DE06_{clip:03d}.mp4',skip_new_generation=True,reason_vi='Cùng bối cảnh hoặc mô hình giảng giải đã có: dùng lại clip, không tạo mới.',specific_edit_note=v))
 else:
  ref=i;clip=len(unique)+1;action='NEW';scene=v;note='';full=f'{clip:03d}. '+common+v+negative
  assert not re.search(r'\b(child|children|infant|boy|girl|adolescent)\b',v,re.I),i
  unique.append(dict(clip_id=clip,first_timeline_scene=i,kind=kind,scene_and_camera=v,all_visible_humans_mature_adults=True,full_prompt=full))
 row=dict(id=i,chapter=chapter,start_seconds=(i-1)*10,end_seconds=i*10,voice_en=voice[i],generation_action=action,skip_new_generation=action=='REUSE',reuse_source_scene=ref,clip_id=clip,filename=f'DE06_{clip:03d}.mp4',kind=kind,scene_and_camera=scene,edit_note=note,visual_children_allowed=False,full_prompt=full);rows.append(row);byid[i]=row
assert len(unique)==110 and len(reuse)==16
for n in range(11):
 group=unique[n*10:n*10+10];text=f'DENISOVA / TOPIC06 / FILE{n+1:02d} /10 SILENT PROMPTS / NO CHILDREN IN ANY VISUAL\n'
 for p in group:
  used=', '.join(f'{x["id"]:03d}' for x in rows if x['clip_id']==p['clip_id']);text+=f'\nCLIP {p["clip_id"]:03d} | FILE DE06_{p["clip_id"]:03d}.mp4 | TIMELINE {used}\n{p["full_prompt"]}\n'
 (O/'PROMPTS'/f'PROMPTS_{n+1:02d}_{group[0]["clip_id"]:03d}_{group[-1]["clip_id"]:03d}.txt').write_text(text)
def stamp(n):return f'{n//3600:02}:{n%3600//60:02}:{n%60:02},000'
words=sum(len(x.split()) for x in voice.values());assert words==3425
(O/'KICH_BAN_EN_21_PHUT.txt').write_text('\n\n'.join(voice.values())+'\n')
timed='DENISOVA: THE PEOPLE HIDDEN IN A FRAGMENT\nOriginal English narration / target21:00 /126 ten-second cues\n'
for r in rows:
 c=chap[r['chapter']-1]
 if r['start_seconds']==c['start_seconds']:timed+=f'\nCHAPTER{r["chapter"]:02d}: {c["title_en"]}\n'
 timed+=f'\n[{r["id"]:03d}] {stamp(r["start_seconds"])} --> {stamp(r["end_seconds"])} | CLIP{r["clip_id"]:03d} | {r["generation_action"]}\n{r["voice_en"]}\n'
(O/'KICH_BAN_EN_CO_MOC.txt').write_text(timed);(O/'LOI_DAN_EN_126_CANH.srt').write_text(''.join(f'{r["id"]}\n{stamp(r["start_seconds"])} --> {stamp(r["end_seconds"])}\n{r["voice_en"]}\n\n' for r in rows))
(O/'SCENES_AND_PROMPTS.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));(O/'UNIQUE_PROMPTS_110.json').write_text(json.dumps(unique,ensure_ascii=False,indent=2))
def csvfile(name,fields,data):
 with (O/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(data)
csvfile('TIMELINE_126_CANH.csv',['id','chapter','start_seconds','end_seconds','clip_id','filename','generation_action','skip_new_generation','reuse_source_scene','voice_en','kind','scene_and_camera','edit_note','visual_children_allowed'],rows);csvfile('CANH_DUNG_LAI_KHONG_TAO_MOI.csv',list(reuse[0]),reuse);csvfile('CHAPTERS_12.csv',list(chap[0]),chap)
hook=[]
for n,(source,sin) in enumerate([(1,0),(21,.3),(11,.5),(4,.5),(2,.5),(28,.5),(35,0),(43,.5),(40,.5),(39,.5),(5,0),(52,.5)]):
 r=byid[source];hook.append(dict(timeline_start=n*2.5,timeline_end=(n+1)*2.5,source_scene=source,clip_id=r['clip_id'],filename=r['filename'],source_in=sin,source_out=sin+2.5,note_vi='12shot trong30giây đầu, không thêm intro, giữ nguyên voice. Mẫu và sơ đồ đều minh họa; chỉ người trưởng thành.'))
csvfile('HOOK_30_GIAY_12_SHOT.csv',list(hook[0]),hook)
sources=json.loads((R/'sources.json').read_text());csvfile('NGUON_KIEM_CHUNG.csv',list(sources[0]),sources)
(O/'NGUON_KIEM_CHUNG.md').write_text('# Nguồn kiểm chứng — Denisova\n\nĐối chiếu ngày10/11/2026.27nguồn nghiên cứu, phương pháp và dự án gốc. Bài năm2026 có ngày công bố09/09 hoặc21/10 trước ngày lập tài liệu. Không sao chép lời video nguồn.\n\n'+'\n\n'.join(f'- **{x["id"]} — {x["title"]} ({x["year"]})**: {x["url"]}\n  DOI: {x["doi"] or "không áp dụng"}. {x["scope"]}' for x in sources)+'\n')
links={}
for i in range(1,127):
 ids=(['S01','S02','S26'] if i<=11 else ['S08','S09','S26'] if i<=22 else ['S04','S05','S27'] if i<=33 else ['S01','S02','S06'] if i<=44 else ['S03','S05','S27'] if i<=55 else ['S07','S10','S11','S12'] if i<=66 else ['S13','S14','S27'] if i<=76 else ['S15','S16','S17'] if i<=86 else ['S18','S10','S11'] if i<=96 else ['S19','S20','S21'] if i<=106 else ['S22','S23','S24'] if i<=116 else ['S25','S03','S27'])
 links[i]=ids
for i in [62,63,64,65]:links[i]=['S12']
for i in [70,71,72]:links[i]=['S14']
for i in [87,88,89]:links[i]=['S18']
for i in [97,98,99]:links[i]=['S19']
for i in [100,101,102,103]:links[i]=['S20','S21']
for i in [107,108]:links[i]=['S22']
for i in [109,110]:links[i]=['S23']
for i in [111,112]:links[i]=['S24']
csvfile('DOI_CHIEU_KHOA_HOC.csv',['cue','start_seconds','source_ids','evidence_note'],[dict(cue=i,start_seconds=(i-1)*10,source_ids=';'.join(links[i]),evidence_note='Narrative questions and analogies are original explanations. No recovered personal biography, exact route, universal phenotype or genome percentage is implied. Sources support the scientific distinctions, not the literal staged scenes.') for i in range(1,127)])
for n in ['BASELINE_VOICE_PROFILES.json','NARRATION_STYLE_LOCKED.json','VOICE_FILE_NAMING.json']:shutil.copy(R/n,O/('VOICE_PROFILES_LOCKED_EXPECTED.json' if n.startswith('BASELINE') else n))
(O/'VOICE_TIMING_THIS_EPISODE.json').write_text(json.dumps(dict(topic=6,seconds=1260,frames_at_48000=60480000,english_cues=126,translated_chapter_seconds=[110]*6+[100]*6,note='Voice identity/style controls unchanged. Baseline duration fields in EXPECTED profiles are historical, not current episode timing.'),indent=2))
analysis='''PHÂN TÍCH NGUỒN VÀ QUY TRÌNH — CHỦ ĐỀ6 DENISOVA

Nguồn: https://github.com/seotro95/seotro/releases/tag/video / video.c.a.toi.mp4. SHA256:f1a8659dbccd4db12a79e3c18ea2e1fe08f46f7a03c42bc2250f454f69eff70c; cùng tệp đã phân tích trong chuỗi, khoảng21:03,1280×720,60fps mã hóa, voiceNga. Đã đối chiếu release hiện tại, contact sheet mở đầu và bản nhận dạng lời dẫn lưu. Không biết phần mềm/prompt thực tế tác giả đã dùng.

NỘI DUNG VÀ KỂ CHUYỆN
Phim tài liệu khoa học phổ thông, lời kể dẫn và hình minh họa, không có người dẫn nói trước máy quay xuyên suốt. Video nguồn mở bằng vật nhỏ và niên đại, đưa ra phát hiện bất ngờ, mở rộng sang cảnh quan, phòng thí nghiệm và câu hỏi lớn; phần nhiều nội dung sau là sinh tồn vùng lạnh. Tập6 học cấu trúc và nhịp dựng, viết lời mới về Denisova, không dịch hoặc lấy giả thuyết Yana thành sự kiện Denisova.

Khung tập6: mảnh xương nhỏ → hồ sơ hang động → kiểm chứng phân tử →2010mtDNA/nuclearDNA →2012genome → dấu vết ở người ngày nay → protein/cao nguyên → trầm tích và sinh kế → giao thoa quần thể → phát hiện2025/2026 → trở lại mảnh xương. Mỗi chương trả lời một câu hỏi rồi đặt vấn đề cho chương sau. Dùng câu hỏi ngắn, động từ rõ, bằng chứng cụ thể và phép so sánh có giới hạn; không hư cấu hội thoại hay tiểu sử.

CÁCH LÀM KỊCH BẢN
3425từAnh mới,126ô10s, tổng1260s.12chương: sáu chương110s rồi sáu chương100s. Không dùng lại ranh120/110s của tập4. Mỗi ô có một ý chính, tối đa29từ; khi tạo voice phải đo thực tế, không coi số từ là chứng nhận thời lượng. Phân biệt năm phát hiện/công bố, tuổi mẫu, khoảng tuổi và tuổi tối thiểu. Một genome không phải cả quần thể; một hình minh họa không phải chân dung thật. Ba ví dụDenisova11 chỉ phục vụ tập6, không tự làm chủ đề7.

TẠO HÌNH VÀ PROMPT
110prompt mới trong11TXT, đúng10prompt/tệp và đánh số001–110.16ôREUSE có nguồn cụ thể trongCSV, không tạo clip mới. Mỗi prompt: một shot liên tục10s, một hành động, một chuyển động máy, hoàn toàn im lặng. Luân phiênmacro vật mẫu, bàn tay trưởng thành, cảnh hang/rừng, thao tác hiện đại, bản đồ và mô hình. ClipDE06_001 không nhất thiết là cảnhtimeline001 khi dùng lại; dựaCSV thay vì tự suy từ tênfile.

Không có hình trẻ em ở bất kỳ nơi nào, kể cả nền, bóng, ảnh, màn hình, tượng và sơ đồ. Người hiện rõ trưởng thành25–60tuổi. Không dựng chủ mẫuDenisova3/Denisova11. Mảnh xương là mô hình giảng giải tách rời; mô hình hàm/răng chỉ có giải phẫu răng vĩnh viễn trưởng thành và không có cơ thể/chân dung. Cảnh kỹ năng cổ dùng diễn viên trưởng thành vô danh, không gán diện mạo/căn tínhDenisovan xác thực. Đồ hiện đại chỉ ở cảnh hiện đại; không đặt bút, sổ, kính lúp hay tấm năng lượng vào cảnh cổ.

DỰNG VIDEO KHI ĐÃ CÓ CLIP
Mở đầu12shot trong30s của voice, không thêm intro. Dựng theo lời: mảnh xương → ghi nhận mẫu/hang →lab/so sánh → phạm vi châu Á. Cắt thẳng theo đổi ý, dissolve ngắn0,4–0,7s khi đổi bối cảnh/quy mô. Hình ngoài trời lạnh tự nhiên, vật mẫuấm trung tính, labtrung tính. Chữ, niên đại và nguồn thêm ởeditor, không yêu cầuAI vẽ chữ hoặc số. Bản đồ dùngPNG khóa nguyên nền; nếuAI làm sai thì pan/zoomPNG trực tiếp. Không dùng cờ, biên giới sắc tộc, tuyến đi chính xác hoặc biểu đồ gene giả.

Video chính sau này chỉ có voiceAnh: loại mọi tiếngclip nguồn, không thêm nhạc/SFX. Dựng đúng1260s; có thể bật/tắt phụ đềAnh. Trước bàn giao, kiểm tra frame/thời lượng, một đường tiếng, đồng bộ nhiều điểm, khoảng đen và giải mã toàn bộ. Bây giờ chỉ bàn giao tài liệu vàvoice, chưa dựngvideo vì chưa cócliptập6.

VOICE VÀ LƯU HỒ SƠ
Bàn giao tài liệu trước, rồi dịch16ngôn ngữ và tạo17voice. Giữ science-prehistory-17-v1:16nam, H’Mông nữ3 từVITS+OpenVoiceV2 củaVoice-Studio-Hmong1.6.6;16bản còn lại dùng backend gốcMelo-Viet-Studio1.3.1. Giữ science-documentary-expressive-v1, điều chỉnh nhịp/nghỉ/nhấn nhẹ trong khả năngengine, không thayID hoặc cao độ. Mỗi voice phải giải mã đúng60.480.000mẫu tại48kHz=1260s. Anh căn126ô10s; bản dịch căn12chương110/100s, không tuyên bố khớp từng từ giữa mọi ngôn ngữ. Dùng tên tệp quốc gia đã khóa, lưuscript/engine/ID/tốc độ/SHA256 và báo cáo cho tập sau. Chất lượng ngôn ngữ và phương ngữH’Mông Trắng vẫn cần người bản ngữ rà soát độc lập.

Chủ đề5 giữ nguyên trong hàng đợi; tập6 được làm theo yêu cầu mới. Không tự chuyển sang tập7.
'''
(O/'PHAN_TICH_NGUON_VA_QUY_TRINH.txt').write_text(analysis)
readme=f'''# Chủ đề6 — Denisova,21phút

**Denisova: The People Hidden in a Fragment**

Kịch bảnAnh mới{words}từ,126mốc10s;110prompt mới trong11TXT và16ôREUSE có đánh dấu. Bộ này được bàn giao trước khi tạo voice; thời lượng âm thanh thực phải được đo sau render.

- KICH_BAN_EN_21_PHUT.txt: lời đọc sạch.
- KICH_BAN_EN_CO_MOC.txt vàLOI_DAN_EN_126_CANH.srt: lời theo mốc.
- PROMPTS/:11tệp, mỗi tệp10prompt mới, đánh số001–110.
- TIMELINE_126_CANH.csv, CANH_DUNG_LAI_KHONG_TAO_MOI.csv: đặt hình và bỏ tạo mới ở16ôdùng lại.
- CHAPTERS_12.csv: sáu chương110s rồi sáu chương100s.
- HOOK_30_GIAY_12_SHOT.csv:12shot mở đầu trong thời gianvoice, không cộngintro.
- NGUON_KIEM_CHUNG, DOI_CHIEU_KHOA_HOC:27nguồn và phạm vi kết luận.
- REFERENCES/: bốn nền bản đồ hiện đại và ba sơ đồ trừu tượng không có hình người.

**Không có hình trẻ em trong bất kỳ prompt nào.** Chỉ người trưởng thành rõ25–60tuổi; loại cả người nền nhỏ khó xác định tuổi, bóng, phản chiếu, ảnh, tượng và màn hình có người trẻ. Không dựng chân dung chủ mẫuDenisova3/Denisova11. Bản đồ là địa lý hiện đại tổng quát, không phải bờ cổ hoặc lộ trình di cư. Sơ đồ là giảng giải, không phải dữ liệu đo.

Tên clipDE06_001.mp4–DE06_110.mp4 khác sốcảnhtimeline001–126. Mọi clip10s không có âm thanh. Thêm toàn bộ chữ và dữ kiện đã đối chiếu trongeditor. Không đặt đồ hiện đại vào bối cảnh cổ.

17voice riêng sẽ giữ đúng mã giọng và nhấn nhá đã lưu;16nam vàH’MôngTrắngnữ3. Mục tiêu mỗi bản21:00/60.480.000mẫu tại48kHz; khớp chương và tổng, không khớp từng từ giữa các ngôn ngữ. Video chính chỉ dùngAnh.21phút là ngoại lệ riêng tập6; không đổi mặc định20phút của chuỗi. Tập5 vẫn xếp hàng, tập7 chưa bắt đầu.
'''
(O/'README.md').write_text(readme)
qa=dict(status='passed',english_words=words,max_words_per_10s_cue=max(len(v.split()) for v in voice.values()),timeline_seconds=1260,timeline_cues=126,unique_prompts=110,reuse_slots=16,prompt_txt_files=11,prompts_per_txt=10,opening_shots=12,no_child_positive_scene_descriptions=True,all_visible_humans_adult_policy=True,audio_status='not_generated_at_document_delivery',target_frames_at_48000=60480000,translated_chapter_durations=[110]*6+[100]*6,source_count=27)
assert all(r['end_seconds']-r['start_seconds']==10 for r in rows);assert sum(c['end_seconds']-c['start_seconds'] for c in chap)==1260
for p in (O/'PROMPTS').glob('*.txt'):assert len(re.findall(r'^CLIP ',p.read_text(),re.M))==10
(O/'DOCUMENT_QA.json').write_text(json.dumps(qa,indent=2));manifest=dict(topic_id=6,title_en='Denisova: The People Hidden in a Fragment',target_seconds=1260,english_words=words,timeline_cues=126,unique_prompts=110,reused_timeline_slots=16,prompt_txt_files=11,prompts_per_txt=10,no_children_in_visuals=True,voice_status='not_generated_at_document_delivery',files=[])
for p in sorted(O.rglob('*')):
 if p.is_file() and p.name!='MANIFEST.json':manifest['files'].append(dict(path=str(p.relative_to(O)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(O/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));archive=R/'DENISOVA_VIDEO_06_TAI_LIEU_21_PHUT.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(O.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(O))
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
summary=dict(words=words,cues=126,new_prompts=110,reuse=16,txt_files=11,seconds=1260,zip_bytes=archive.stat().st_size,zip_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),file_count=len(manifest['files'])+1)
(R/'DOCUMENT_BUILD.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
