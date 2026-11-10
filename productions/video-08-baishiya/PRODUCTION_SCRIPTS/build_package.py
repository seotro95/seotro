import csv,hashlib,json,re,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;O=R/'package';O.mkdir(exist_ok=True);(O/'PROMPTS').mkdir(exist_ok=True)
p=R/'visuals.tsv';p.write_text(p.read_text().replace('90\t=82\tREUSE ecological mosaic cue82; shift toward long-time-scale narration with an editor-created chapter card, do not imply this is a measured ancient habitat map.','90\tLANDSCAPE\t35mm static wide view of an empty northeastern Tibetan Plateau grass valley as a single broad cloud shadow moves gently over adjacent open slopes and shrub patches; ordinary within-day light change, no accelerated climate morphing, people, buildings, text or implied exact prehistoric map.'))
voice={int(a):b for a,b in (l.split('\t',1) for l in (R/'script_en.tsv').read_text().splitlines())};vis={int(a):(b,c) for a,b,c in (l.split('\t',2) for l in p.read_text().splitlines())};assert set(voice)==set(vis)==set(range(1,135))
titles=[('A cave above the valley','Hang động trên thung lũng'),('The jaw that changed the map','Mảnh hàm thay đổi bản đồ'),('Reading the animal archive','Đọc hồ sơ xương động vật'),('The physical cost of a meal','Cái giá thể lực của bữa ăn'),('Marks that preserve actions','Dấu vết giữ lại hành động'),('Energy behind a hard shell','Năng lượng sau lớp xương cứng'),('More than food','Không chỉ là thức ăn'),('A mosaic of opportunities','Nhiều sinh cảnh, nhiều cơ hội'),('Time, gaps and the fire question','Thời gian, khoảng trống và câu hỏi về lửa'),('The person among animal fragments','Mảnh xương người giữa xương động vật'),('Bodies, inheritance and knowledge','Cơ thể, di truyền và hiểu biết'),('What the fragments let us see','Điều các mảnh xương cho thấy')]
chap=[];t=0
for n,((en,vi),count) in enumerate(zip(titles,[12,12]+[11]*10),1):chap.append(dict(chapter=n,start_seconds=t,end_seconds=t+count*10,cue_count=count,title_en=en,title_vi=vi));t+=count*10
assert t==1340
common='One continuous 10-second shot, 16:9, target1920x1080,24fps when supported. Cinematic evidence-led prehistory documentary, tactile natural materials, restrained contrast, realistic geography and motion. One principal action and one slow motivated camera move. '
negative=' Completely silent video: no audio stream, speech, narration, music, ambience, animal sounds, wind sounds or sound effects. No children, babies, infants, adolescents or anyone under18 anywhere, including background, distance, silhouettes, shadows, reflections, photographs, posters, screens, statues or diagrams. Any visible human must be unmistakably a mature adult aged25–60; any hands must visibly belong to mature adults. No identified portrait or bodily reconstruction of a fossil owner. Animal bone replicas must remain nonhuman; any isolated jaw teaching cast must show mature permanent dentition with no attached face or body. No human skeleton, juvenile anatomy, skull spectacle, blood, gore or hunting kill. No generated text, dates, numbers, letters, subtitles, graphs, maps, genetic sequences, flags, logos or watermarks. Modern lab/field scenes remain modern; anonymous ancient skill demonstrations use only plausible stone, wood, hide and fibre, never metal, zippers, needles, pens, notebooks, computers, glass vials, solar panels or modern furniture. No prehistoric hearth, torch or proved fire-use scene. No Everest-like giant mountains, Arctic ice desert, mammoths or igloos. No claim this is actual recovered ancient footage or an exact Denisovan likeness, costume or culture. Add all verified labels and illustrative disclaimers in editing.'
rows=[];unique=[];reuse=[];byid={}
for i in range(1,135):
 kind,v=vis[i];chapter=next(c['chapter'] for c in chap if c['start_seconds']<i*10<=c['end_seconds']);ref=i
 if kind.startswith('='):
  ref=int(kind[1:]);src=byid[ref];assert src['generation_action']=='NEW';clip=src['clip_id'];action='REUSE';full=src['full_prompt'];scene=src['scene_and_camera'];kind=src['kind'];note=v
  reuse.append(dict(timeline_scene=i,start_seconds=(i-1)*10,end_seconds=i*10,reuse_source_scene=ref,clip_id=clip,filename=f'BS08_{clip:03d}.mp4',skip_new_generation=True,reason_vi='Dùng lại bối cảnh đã có; bỏ tạo clip mới.',specific_edit_note=v))
 else:
  clip=len(unique)+1;action='NEW';scene=v;note='';full=f'{clip:03d}. '+common+v+negative
  unique.append(dict(clip_id=clip,first_timeline_scene=i,kind=kind,scene_and_camera=v,full_prompt=full))
 row=dict(id=i,chapter=chapter,start_seconds=(i-1)*10,end_seconds=i*10,voice_en=voice[i],generation_action=action,skip_new_generation=action=='REUSE',reuse_source_scene=ref,clip_id=clip,filename=f'BS08_{clip:03d}.mp4',kind=kind,scene_and_camera=scene,edit_note=note,visual_children_allowed=False,full_prompt=full);rows.append(row);byid[i]=row
assert len(unique)==120 and len(reuse)==14
for n in range(12):
 g=unique[n*10:n*10+10];txt=f'BAISHIYA / TOPIC08 / FILE{n+1:02d} /10 SILENT PROMPTS / NO CHILDREN ANYWHERE\n'
 for x in g:txt+=f'\nCLIP{x["clip_id"]:03d} | BS08_{x["clip_id"]:03d}.mp4 | TIMELINE '+','.join(f'{a["id"]:03d}' for a in rows if a['clip_id']==x['clip_id'])+'\n'+x['full_prompt']+'\n'
 (O/'PROMPTS'/f'PROMPTS_{n+1:02d}_{g[0]["clip_id"]:03d}_{g[-1]["clip_id"]:03d}.txt').write_text(txt,encoding='utf-8-sig')
def stamp(n):return f'{n//3600:02}:{n%3600//60:02}:{n%60:02},000'
def write(n,s): (O/n).write_text(s,encoding='utf-8-sig' if n.endswith('.txt') else 'utf-8')
write('KICH_BAN_EN_22m20s.txt','\n\n'.join(voice.values())+'\n')
write('KICH_BAN_EN_CO_MOC.txt','BAISHIYA: THE SURVIVAL STORY HIDDEN IN BROKEN BONES\nOriginal script /22:20 /134cues\n'+'\n'.join(f'\n[{r["id"]:03d}] {stamp(r["start_seconds"])} --> {stamp(r["end_seconds"])} | CHAPTER{r["chapter"]:02d} | CLIP{r["clip_id"]:03d} | {r["generation_action"]}\n{r["voice_en"]}' for r in rows))
write('LOI_DAN_EN_134_CANH.srt',''.join(f'{r["id"]}\n{stamp(r["start_seconds"])} --> {stamp(r["end_seconds"])}\n{r["voice_en"]}\n\n' for r in rows))
write('SCENES_AND_PROMPTS.json',json.dumps(rows,ensure_ascii=False,indent=2));write('UNIQUE_PROMPTS_120.json',json.dumps(unique,ensure_ascii=False,indent=2))
def csvfile(n,data,fields=None):
 with (O/n).open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=fields or list(data[0]),extrasaction='ignore');w.writeheader();w.writerows(data)
csvfile('TIMELINE_134_CANH.csv',rows,['id','chapter','start_seconds','end_seconds','clip_id','filename','generation_action','skip_new_generation','reuse_source_scene','voice_en','kind','scene_and_camera','edit_note','visual_children_allowed']);csvfile('CANH_DUNG_LAI_KHONG_TAO_MOI.csv',reuse);csvfile('CHAPTERS_12.csv',chap)
hook=[]
for n,(scene,ins) in enumerate([(1,0),(5,1),(31,1),(3,1),(9,1),(63,1),(2,0),(19,1),(100,1),(104,1),(4,1),(12,1)]):
 r=byid[scene];hook.append(dict(timeline_start=n*2.5,timeline_end=(n+1)*2.5,source_scene=scene,clip_id=r['clip_id'],filename=r['filename'],source_in=ins,source_out=ins+2.5,note_vi='Hook12shot/30s nằm trong voice, không cộng intro; minh họa, không phải footage cổ thực.'))
csvfile('HOOK_30_GIAY_12_SHOT.csv',hook)
sources=[
('S01','Xia etal.2024, Middle and Late Pleistocene Denisovan subsistence at Baishiya Karst Cave','https://pmc.ncbi.nlm.nih.gov/articles/PMC11291277/','10.1038/s41586-024-07612-9','Site3280m;2567specimens,1857ZooMS;caprines;modifications;tools;rib;chronological and taxonomic limits. CC BY4.0, original narrative adaptation; no figures copied.'),
('S02','Xia etal.2024, Supplementary Information','https://pure.mpg.de/rest/items/item_3599690_3/component/file_3599696/content','10.1038/s41586-024-07612-9','Burned bones limited; human versus natural burning unresolved. Three expedient bone tools;possible tooth retoucher. No invented hearth.'),
('S03','Chen etal.2019, A late Middle Pleistocene Denisovan mandible from the Tibetan Plateau','https://doi.org/10.1038/s41586-019-1139-x','10.1038/s41586-019-1139-x','Xiahe1:1980find,minimum~160ka from carbonate crust,protein-based Denisovan connection,not excavated stratigraphic provenience.'),
('S04','MaxPlanck2019, First hominins on the Tibetan Plateau were Denisovans','https://www.eva.mpg.de/de/press/news/2019-05-01-101405-first-hominins-on-the-tibetan-plateau-were-denisovans/','','Institutional public explanation of mandible discovery and proteomic identification.'),
('S05','Zhang etal.2020, Denisovan DNA in Late Pleistocene sediments from Baishiya Karst Cave','https://pubmed.ncbi.nlm.nih.gov/33122381/','10.1126/science.abb6320','Sedimentary mitochondrialDNA~100ka60ka possibly45ka;not a complete nuclear genome or proof of uninterrupted occupation.'),
('S06','Huerta-Sanchez etal.2014, Altitude adaptation in Tibetans caused by introgression of Denisovan-like DNA','https://pmc.ncbi.nlm.nih.gov/articles/PMC4134395/','10.1038/nature13408','Modern TibetanEPAS1region Denisovan-related ancestry and haemoglobin association;not physiology/genome of Xiaheindividual.'),
('S07','Zhang etal.2021, The history and evolution of the Denisovan-EPAS1 haplotype in Tibetans','https://pmc.ncbi.nlm.nih.gov/articles/PMC8179186/','','Introgression history versus plateau settlement;no one gene superpower or personal biography.'),
('S08','Brown etal.2016, Identification of a new hominin bone from Denisova Cave using collagen fingerprinting and mitochondrial DNA analysis','https://pmc.ncbi.nlm.nih.gov/articles/PMC4810434/','10.1038/srep23559','ZooMS screening and follow-up distinction;not all close-hominin screens identify Denisovans alone.'),
('S09','NCBI Bookshelf, Physiology: High-Altitude Oxygenation','https://www.ncbi.nlm.nih.gov/sites/books/NBK539701/','','Reduced barometric/partial pressure,oxygenfraction~21% retained;not exact personal medical state.'),
('S10','USDA National Agricultural Library, Food and Nutrition Information Center','https://www.nal.usda.gov/programs/fnic','','Fat supplies concentratedenergy9kcal/g;no reconstructed daily calorie budget.'),
('S11','IUCN2014, Pseudois nayaur assessment','https://doi.org/10.2305/IUCN.UK.2014-3.RLTS.T61513537A64313015.en','','Modern species habitat/grassland ecology,not exact ancient prey behaviour or proven hunt.'),
('S12','Animal Diversity Web, Pseudois nayaur','https://animaldiversity.org/accounts/Pseudois_nayaur/','','Modern species morphology/ecology;muted coat,realistic slope movement,not bright blue animal.'),
('S13','User reference video release','https://github.com/seotro95/seotro/releases/tag/video','','Editing and narrative observation only;Russianvoice,Yana/Arctic topic;not Baishiya factual source. SHA256:f1a8659dbccd4db12a79e3c18ea2e1fe08f46f7a03c42bc2250f454f69eff70c.')]
src=[dict(id=a,title=b,url=c,doi=d,scope=e,checked_utc='2026-11-10') for a,b,c,d,e in sources];csvfile('NGUON_KIEM_CHUNG.csv',src)
write('NGUON_KIEM_CHUNG.md','# Nguồn và phạm vi sử dụng\n\n'+'\n\n'.join(f'- **{x["id"]} — {x["title"]}**: {x["url"]}\n  {x["scope"]}' for x in src)+'\n\nBài chính2024 làCCBY4.0;ghi côngXia vàcộngsự,Nature632,108–113,DOI10.1038/s41586-024-07612-9. Kịch bản diễn giải mới,không sao chép hình/bảng. Nguồnthamkhảodựngkhôngđượctáixuấtbản.\n')
checks=[]
for r in rows:
 i=r['id'];ids=['S01']
 if i<=12:ids+=['S09']
 if 13<=i<=20:ids=['S03','S04']
 if i==21:ids=['S05']
 if 28<=i<=30 or 102<=i<=104:ids+=['S08']
 if 31<=i<=39:ids+=['S11','S12']
 if 58<=i<=68:ids+=['S10']
 if 96<=i<=98:ids+=['S02']
 if 113<=i<=118:ids=['S06','S07']
 checks.append(dict(cue=i,source_ids=';'.join(ids),evidence_status='Narrative questions, demonstrations and practical constraints are original explanation;not reconstructed biography. Counts refer to specimens. Layer age not exact death date. No continuous occupation or proven hearth inferred.'))
csvfile('DOI_CHIEU_KHOA_HOC.csv',checks)
for n in ['NARRATION_STYLE_LOCKED.json','VOICE_FILE_NAMING.json']:shutil.copy(R/n,O/n)
shutil.copy(R/'BASELINE_VOICE_PROFILES.json',O/'VOICE_PROFILES_LOCKED_EXPECTED.json')
write('VOICE_TIMING_THIS_EPISODE.json',json.dumps(dict(topic=8,seconds=1340,frames_at_48000=64320000,english_cues=134,translated_chapter_seconds=[120]*2+[110]*10,note='Preserve17 voice identities/style;historical baseline durations do not apply to8.'),indent=2))
write('PHAN_TICH_NGUON_VA_QUY_TRINH.txt','''CHỦ ĐỀ8 — BAISHIYA /22:20

Nguồn tham khảo: https://github.com/seotro95/seotro/releases/tag/video . CùngvideoSHA256f1a8659dbccd4db12a79e3c18ea2e1fe08f46f7a03c42bc2250f454f69eff70c, khoảng21:03,1280×720,60fpsmãhóa,lờiNga. Đã xem contact sheet/phân tích lời mở đầu. Tác giả không công bố phần mềm/prompt,không khẳng định biết chúng.

Dạng nội dung: tài liệu khoa học phổ thông có lời dẫn,hìnhminhhọa,vật nhỏ mở câu hỏi lớn. Cách kể nguồn: manhmối→địađiểm/niênđại→pháthiện→kiểmchứnglab→sinhtồn→callback. Luânphiênmacro,cảnhquan,thao tác,bảnđồ;cắt theo đổi ý,dissolve ngắn đổi thời gian/quy mô. Học nhịp kể và dựng,không dịch lời hoặc dùngcảnhtrẻem/cờcủanguồn. Baishiya dùng nguồn khoa học riêng.

Kịch bản mới3162từAnh,134ô10s.12chương:2chương120s,10chương110s. Mở bằng sức ép độ cao,nhá mảnh xương người giữa xương động vật;rồi làm rõ danh tính sớm,đưa ra từng lời giải thực tế:địa hình→dấu cắt→tủy→da/côngcụ→đa dạng nguồn→khoảngtrốngthờigian→mảnhsườn→di truyền→callback. Mỗi chương giải một câu hỏi rồi mở câu kế. Không hư cấu hội thoại,cảnh săn cụ thể,cá nhân,cơ thể,gene của chủ mẫu. Nhịp22–26từ/10s có chỗ nghỉ/nhấn;thời lượng phải đo sau render.

120promptmới/12TXT,đúng10prompt/tệp,đánhsố001–120.14ôREUSE đã chỉ nguồn trongCSV:không tạo clip mới. Timeline001–134 khácclipBS08_001–120. Cảnh một hành động,một chuyểnđộngmáy,chuyển đổi18–35mmrộng,50mmtrung,85mmthao tác,100mmmacro. Phần lớn cảnhquan/độngvật/vậtmẫu/kỹnăng;labchỉcầnnơiđưa bằng chứng. Chỉ người trưởngthành rõ25–60tuổi. Khôngtrẻem kể cả nền,bóng,ảnh,mànhình,tượng/sơđồ;không táihiệnchủhóa thạch. Vật xương minh họa là mô hình động vật khôngphảingười;hàmgiảnggiải chỉrăngvĩnhviễntrưởngthành. Khôngsẹo,blood/gore/cảnhgiếtsăn. Độngvậtlớntrưởngthành,khôngconnon.

Không dùngAIvẽbảnđồ,chữ,số,dữliệugene. Thêmtrongeditor từnguồnđãđốichiếu. Địađiểm35.45N102.57E,3280m,tâybắcTrungQuốc/đôngbắcTâyTạng;Denisova51.40N84.68Echỉlàmđiểmso sánh,khôngvẽtuyếnđiđãchứngminh. Mọi táihiệnkỹnăngđềughiminhhọa,bối cảnhcổchỉđá/gỗ/da/sợi,khôngkimloại,bút,sổ,kínhlúp,solarpanel,zippers. KhôngdựngbếplửacổởBaishiyanhưsựkiệnđãchắcchắn.

Hook30s:12shot×2.5s,theoCSV,từcảnhquan→ngườitrưởngthànhđingược dốc→bharal→hang→dấucắt→thao tác→khayxương→lab→mẫuđóngkín→hang. Nằmtrongvoice,khôngintrothêm. Dựngfullhardcuttheoý;chỉdissolve0.35–0.65skhiđổiđịađiểm/quymô,khôngtransitiontrànlan. Ánhsángngoàitrờitựnhiên,labtrungtính,macroấmnhẹ;khôngrung/zoomgiậtliêntục. Chữrõngắn,nguồnnhoởgóchiệntheomốc,khônggiảsốliệu. Xóatiếngclipgốc,toànbộclipyêucầukhôngâmthanh;videochínhsauchỉvoiceAnh,khôngnhạc/SFX.

Voice:16namcùngIDđãlưu,H’MôngTrắngnữ3cùngpresetnativeVITS+OpenVoiceV2. Nhấnnhánhẹtheocâuhỏi/bằngchứng/kếtluận,khôngthaycaođộhayID. Anh134ô10s;bảndịch12chương120/110s. Mỗifilegiảimã64.320.000mẫutại48kHz=1340s;khớpchương/tổng,khôngtuyênbốkhớptừngtừgiữangônngữ. Têntệptheoquốcgia;giữengine/sourcecommit/presetSHA256/kiểuđọctronghồsơ. Bảndịch/giọngcầnbảnngữràsoátđộ tựnhiên,đặcbiệtphươngngữH’MôngTrắng.

Lưutiếntrìnhtập8,danhmụcclip/script/prompt/nguồn/voice/QAtrongGitHub. Giữkếtquả1–4,6;tập5,7vẫnqueued,khôngtựlàmtập9. Chưa cóclipmớiđểdựngvideo8;khôngtạolinktảivideogiả.
''')
write('README.md','''# Chủ đề8 — Baishiya,22:20

**Baishiya: The Survival Story Hidden in Broken Bones**

Kịch bảnAnh3162từ/134mốc10s.120promptmới/12TXT,mỗiTXT10prompt;14mốcREUSEđãđánhdấuCSV. ClipBS08_001–120 khác sốtimeline001–134. Không cótrẻem ởbấtkỳ đâu;chỉngườitrưởngthành25–60tuổi,độngvậttrưởngthành. Tấtcảclipkhôngâmthanh.

Đọc KICH_BAN_EN_22m20s.txt hoặc bản CO_MOC;dùng TIMELINE_134_CANH.csvđểgắnhìnhvà CANH_DUNG_LAI_KHONG_TAO_MOI.csvđểbỏtạocảnhtrùng. HOOK_30_GIAY_12_SHOT.csvquyđịnh12shottrong30svoiceđầu,khôngcộngintro. Chương1–2:120s;3–12:110s.

Phân tích nguồn/quy trình trongPHAN_TICH_NGUON_VA_QUY_TRINH.txt;nguồn/giớihạnbằngchứngtrongNGUON_KIEM_CHUNGvàDOI_CHIEU_KHOA_HOC. NghiêncứuchínhXiaetal.2024CCBY4.0đãghicông,kịchbảnmới,khôngsaochéphình. Mảnhhàmminimum160ka;mảnhsườnlayer3~48–32ka;khônggánngàychếtchínhxác,khôngbếplửachắcchắn,khônggenephépmàu.

Bộdocumentsđượcbàngiaotrướcvoice.17voicegiữID/styleđãkhóa:16nam,H’MôngTrắngnữ3. Mỗifile1340s/64.320.000mẫu48kHzsaukhiđo;Anh134ô10s,bảndịch12chương,khôngkhớptừngtừgiữacácngônngữ. Tênfiletheoquốcgia. Khôngtuyênbốđãcóaudionếuchưarender/kiểmtra. Chưadựngvideovìchưacóclip8.
''')
words=sum(len(s.split()) for s in voice.values());assert words==3162
qa=dict(status='passed',english_words=words,minimum_words_per_cue=min(len(s.split()) for s in voice.values()),maximum_words_per_cue=max(len(s.split()) for s in voice.values()),timeline_seconds=1340,timeline_cues=134,new_prompts=120,reuse_slots=14,prompt_txt_files=12,prompts_per_txt=10,hook_shots=12,no_children_policy_in_every_prompt=True,silent_policy_in_every_prompt=True,source_count=len(src),audio_status='not_yet_generated',target_frames_48000=64320000)
for q in (O/'PROMPTS').glob('*.txt'):assert len(re.findall(r'^CLIP\d',q.read_text(encoding='utf-8-sig'),re.M))==10
write('DOCUMENT_QA.json',json.dumps(qa,indent=2));manifest=dict(topic=8,seconds=1340,files=[])
for f in sorted(O.rglob('*')):
 if f.is_file() and f.name!='MANIFEST.json':manifest['files'].append(dict(path=str(f.relative_to(O)),bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
write('MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
archive=R/'BAISHIYA_VIDEO_08_TAI_LIEU_22m20s.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for f in sorted(O.rglob('*')):
  if f.is_file():z.write(f,f.relative_to(O))
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
info=dict(**qa,zip_bytes=archive.stat().st_size,zip_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),file_count=len(manifest['files'])+1)
(R/'DOCUMENT_BUILD.json').write_text(json.dumps(info,indent=2));print(json.dumps(info))
