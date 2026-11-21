import csv,hashlib,json,re,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;C=json.loads((R/'EPISODE.json').read_text());D=R/'documents';P=D/'PROMPTS';S=R/'voice/scripts'
for p in [D,P,S]:p.mkdir(parents=True,exist_ok=True)
T=C['target_seconds'];PREFIX=C['prefix'];BASE=f"https://github.com/seotro95/seotro/releases/download/{C['release_tag']}/"
def dump(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def stamp(t):return f'{t//3600:02}:{t%3600//60:02}:{t%60:02},000'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
raw=[x.split('\t') for x in (R/'CUES_MASTER.tsv').read_text().splitlines()];assert len(raw)==C['english_cues'] and all(len(x)==8 for x in raw)
rows=[dict(id=int(i),section=int(sec),start=int(a),end=int(b),kind=k,voice=v,visual=vis,mode=mode) for i,sec,a,b,k,v,vis,mode in raw]
assert rows[0]['start']==0 and rows[-1]['end']==T and all(a['end']==b['start'] for a,b in zip(rows,rows[1:]))
assert all(3<=x['end']-x['start']<=10 and not re.search(r'\d',x['voice']) for x in rows)
voice=[{k:x[k] for k in ['id','start','end','voice']} for x in rows]
dump(S/'en-US.json',voice);dump(D/f'ENGLISH_CUES_{C["english_cues"]}.json',voice);dump(D/'CUES_WITH_SCENES.json',rows)
hooks=[x['start'] for x in rows if x['kind']=='rehook'];caveats=[x for x in rows if x['kind']=='caveat'];gaps=[b-a for a,b in zip(hooks,hooks[1:])];cg=[b['start']-a['start'] for a,b in zip(caveats,caveats[1:])]
assert min(gaps)>=60 and max(gaps)<=90 and min(cg)>=120 and len(caveats)==C['translated_sections']
assert rows[0]['end']==10 and rows[2]['end']<30 and rows[4]['start']<120
assert rows[-1]['voice']=='Whose story still waits in the undisturbed ground?'
assert all(any(x['kind']=='scene' for x in rows if x['section']==i) for i in range(1,C['translated_sections']+1))
ret=dict(status='passed',version='retention-v5',hook_object='one angular stone slab',first_shot_seconds=10,promise_cue_id=3,promise_completed_seconds=rows[2]['end'],first_payoff_cue_id=5,first_payoff_start_seconds=rows[4]['start'],rehook_starts=hooks,rehook_gaps_seconds=gaps,max_rehook_gap=max(gaps),caveat_cue_ids=[x['id'] for x in caveats],caveat_start_gaps_seconds=cg,min_caveat_gap=min(cg),caveats_per_section=1,caveat_beat_seconds=[x['end']-x['start'] for x in caveats],sections=C['translated_sections'],each_section_has_present_tense_scene=True,section_endings_are_turn_or_question=True,voice_cue_duration_values=sorted({x['end']-x['start'] for x in rows}),all_english_numbers_spelled_out=True,final_single_mystery=rows[-1]['voice'],review_method='Deterministic timing and annotation checks plus assistant editorial review; no measured viewer-retention claim')
dump(D/'RETENTION_QA.json',ret);dump(D/'RETENTION_RULES_LOCKED.json',dict(version='retention-v5',first_ten_seconds_one_object=True,promise_before_seconds=30,first_payoff_before_seconds=120,rehook_every_seconds=[60,90],minimum_gap_caveat_beats_seconds=120,voice_blocks_seconds=[3,10],present_tense_scene_each_section=True,each_section_ends_on_turn=True,english_numbers_as_words=True,ending_answers_then_one_mystery=True,no_auto_start_next_topic=True))
chapters=[]
for i in range(1,C['translated_sections']+1):
 g=[x for x in rows if x['section']==i];chapters.append(dict(id=i,start=g[0]['start'],end=g[-1]['end'],source_cue_ids=[x['id'] for x in g],voice=' '.join(x['voice'] for x in g)))
assert [x['end']-x['start'] for x in chapters]==C['section_seconds'];dump(D/f'SECTIONS_{C["translated_sections"]}_FULL_EN.json',chapters)
opening=[
('The exact same pale sandstone comparison slab, one pre-existing sharp angular corner and one narrow sediment band visible. One concrete object only; no person, hill reveal, cutaway, or other object enters during this first shot.','macro',0,10),
('The exposed natural layer in the foreground leads toward an irregular wooded triangular hill in a plausible central Bosnian valley.','landscape',10,14),
('A lateral view reveals the wooded hill connecting to less regular neighboring ridges, ordinary green terrain and no artificial pyramid casing.','landscape',14,18),
('The same slab and its adjoining continuous layer remain physically connected as the camera reveals the boundary, not an isolated cut block.','macro',18,22),
('Clearly adult anonymous observer stands beside the same outcrop on a path and follows the sediment band without touching or removing stone.','field',22,26),
('The thin sediment band continues from the slab across a pre-existing fracture into the neighboring solid rock, the first concrete continuity clue.','macro',26,30)]
shots=[dict(id=i+1,start=a,end=b,visual=v,mode=m,kind='opening',used=True) for i,(v,m,a,b) in enumerate(opening)]
for start in range(30,T-2,10):
 end=start+10;mid=(start+end)/2;key=next(x for x in rows if x['start']<=mid<x['end']);shots.append(dict(id=len(shots)+1,start=start,end=end,visual=key['visual'],mode=key['mode'],kind='main',used=True))
shots.append(dict(id=len(shots)+1,start=T-2,end=T,visual=rows[-1]['visual'],mode=rows[-1]['mode'],kind='ending',used=True))
assert len(shots)==C['timeline_shots'] and sum(x['end']-x['start'] for x in shots)==T
backup=[('The same opening angular slab and continuous adjoining rock layer under gentle raking daylight, stable grains and existing fracture.','macro'),('A modest regional medieval wall comparison rests on a natural layered hillside model, clearly different construction and geological scales.','model')]
for v,m in backup:shots.append(dict(id=len(shots)+1,start=None,end=None,visual=v,mode=m,kind='backup_not_on_timeline',used=False))
assert len(shots)==C['prompt_count'] and [x['id'] for x in shots if not x['used']]==C['backup_ids']
cameras={
'macro':['Macro 100 mm slow lateral slide along the material boundary, readable depth of field.','Close 85 mm oblique push toward the existing corner, keep all grains and contacts stable.','Macro 90 mm restrained focus pull from surface grains to the adjacent layer, no object morphing.'],
'field':['Medium 50 mm measured side track from an established path, stable ground-level perspective.','Low 35 mm gentle forward move revealing material continuity and surrounding context.','Medium 65 mm steady lateral reveal, maintain credible distances and adult anatomy.'],
'landscape':['Wide 24 mm restrained lateral aerial drift above a plausible wooded valley, natural irregular terrain.','Long 85 mm slow side move from a valley viewpoint, preserve realistic ridge depth and parallax.','Wide 35 mm gentle forward reveal across green hills, no invented perfect geometry.'],
'model':['High oblique 50 mm slow arc around the fixed outdoor physical teaching model.','Low 65 mm side track along the open section, retain every material contact.','Overhead 50 mm slow diagonal movement across clearly separate comparison stages.'],
'heritage':['Medium 50 mm slow push from a safe established path toward modest masonry contacts.','Wide 35 mm quiet lateral move connecting low ruins with surrounding natural bedrock.','Close 85 mm side slide along stable wall-base relationships without entering fragile areas.'],
'history':['Medium 50 mm quiet side track showing credible adult hand work and stone supports.','Wide 35 mm slow forward reveal of a modest outdoor regional medieval working scene.'],
'deep_time':['Wide 35 mm slow lateral drift across a clearly illustrative ancient river-and-basin reconstruction.','Low 50 mm restrained move following sediment settling in shallow water, no time-lapse rock formation.']}
silent='Video không có âm thanh, không có lời nói.'
for x in shots:
 overlap=[r for r in rows if x['used'] and r['start']<x['end'] and r['end']>x['start']]
 x.update(generation_seconds=10,use_seconds=x['end']-x['start'] if x['used'] else 0,source_filename=f'BOSNIA_{x["id"]:03}.mp4',voice_cue_ids=[r['id'] for r in overlap],voice=' '.join(r['voice'] for r in overlap),section_ids=sorted({r['section'] for r in overlap}),setting='outdoor',camera=cameras[x['mode']][(x['id']-1)%len(cameras[x['mode']])])
 extra=('Historical scene: ordinary regional medieval practice, all characters clearly adult, plausible wool or linen clothing; no named historical individual, exact Visoki reconstruction, pyramid-building workforce, or claimed recorded event. ' if x['mode']=='history' else 'Deep-time reconstruction contains no people, buildings, modern tools, dinosaurs, or decorative animals. ' if x['mode']=='deep_time' else '')
 x['prompt']=('One continuous 10-second shot, landscape 16:9, cinematic outdoor archaeology and geology documentary, natural light, restrained purposeful movement. '+x['visual']+' Camera: '+x['camera']+' '+extra+
 'Use a green central Bosnian valley palette, pale stone, forested irregular slopes and realistic modest relief. These scenes are illustrative reconstructions, comparison replicas, or separate teaching models, not authenticated Visoko excavation footage, a measured terrain survey, recovered dated specimens, or a verified site plan. '
 'Keep natural sediment layers and fractures distinct from deliberately assembled masonry. Models are visibly physical, separate from the landscape, simplified and not to scale. Do not generate a giant built pyramid, smooth artificial casing, precise symmetrical pyramid faces, Mayan steps, hidden palace, treasure, alien builders, energy beam, glowing stones, fake radar plot, or invented analytical results. '
 'No destructive collecting, digging into real ruins, sudden real-landscape deformation, magically moving layers, or material morphing. No laboratory, white coats, indoor scientist scene, microscope, or clinical room. Prioritize outdoor hills, outcrops, heritage context, and physical comparison models. '
 'No children, infants, adolescents, minors, or minors in backgrounds, shadows, screens, images, and reflections. Every visible person or hand must clearly belong to an adult age 35–65. No human remains or skulls. '
 'No readable words, writing, letters, dates, numbers, labels, captions, signs, logos, institutional seals, or watermark. Screens face away; no data overlays. Keep terrain, objects, contacts, and anatomy stable. '+silent)
assert len({x['prompt'] for x in shots})==C['prompt_count']
for i in range(0,len(shots),10):(P/f'PROMPT_{i//10+1:02}_{i+1:03}-{i+10:03}.txt').write_text('\n\n'.join(f"{x['id']:03}. {x['prompt']}" for x in shots[i:i+10])+'\n',encoding='utf-8')
dump(D/'ALL_PROMPTS.json',shots);dump(D/f'OPENING_{C["opening_shots"]}_SHOTS_30s.json',shots[:C['opening_shots']]);dump(D/'BACKUP_129_130.json',shots[C['timeline_shots']:])
fields=['id','start','end','use_seconds','generation_seconds','voice_cue_ids','voice','source_filename','kind','mode','setting','visual','camera','prompt']
for name,subset in [(f'TIMELINE_{C["timeline_shots"]}_CANH.csv',shots[:C['timeline_shots']]),(f'PROMPT_INDEX_{C["prompt_count"]}.csv',shots)]:
 with (D/name).open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(subset)
(D/f'KICH_BAN_EN_{C["duration_label"]}.txt').write_text('\n\n'.join(x['voice'] for x in rows)+'\n',encoding='utf-8')
(D/'KICH_BAN_EN_CO_MOC.txt').write_text('\n\n'.join(f"{x['id']:03} | {stamp(x['start'])} → {stamp(x['end'])} | PHẦN {x['section']} | {x['kind']}\n{x['voice']}" for x in rows)+'\n',encoding='utf-8')
(D/'en-US.srt').write_text('\n\n'.join(f"{x['id']}\n{stamp(x['start'])} --> {stamp(x['end'])}\n{x['voice']}" for x in rows)+'\n',encoding='utf-8')
for n in ['EPISODE.json','SOURCE_ASSET_MANIFEST.json','SOURCES_REGISTER.json','NGUON_KIEM_CHUNG.md','PHAN_TICH_VA_KE_HOACH_DUNG.md','PRODUCTION_STEPS_APPLIED.md','5_TIEU_DE_VA_THUMBNAIL.txt','VOICE_PROFILES_LOCKED_BASELINE.json','MELO_SOURCE_LOCK.json']:shutil.copyfile(R/n,D/n)
words=sum(len(re.findall(r"\b[\w'-]+\b",x['voice'])) for x in rows)
qa=dict(status='passed',topic_id=C['topic_id'],catalogue_id='new-100-topics-20261116',target_seconds=T,english_words=words,english_wpm=round(words/(T/60),3),english_cues=len(rows),voice_cue_duration_values=ret['voice_cue_duration_values'],unique_prompts=C['prompt_count'],prompt_txt_files=C['prompt_txt_files'],prompts_per_txt=10,timeline_shots=C['timeline_shots'],backup_prompt_ids=C['backup_ids'],timeline_total_seconds=T,opening_shots=C['opening_shots'],opening_seconds=30,first_shot_seconds=10,all_prompts_silent_suffix=True,all_prompts_exclude_minors=True,translated_sections=C['translated_sections'],section_seconds=C['section_seconds'],expected_audio_frames_48000=C['frames'],requested_voice_count=16,all_requested_voices_male=True,vietnamese_voice_id='vi-VN-NamMinhNeural',voices_generated=False,footage_generated=False,thumbnail_generated=False,video_edited=False,visual_revision='bosnia-outdoor-evidence-v5',outdoor_scenes=C['prompt_count'],laboratory_scenes=0,authentic_site_imagery_included=False,retention_qa_status='passed',claim_treatment='Natural-hill interpretation supported; distinguish genuine medieval heritage and other human activity from unestablished giant-pyramid construction claim')
dump(D/'DOCUMENT_QA.json',qa)
(D/'HUONG_DAN_SU_DUNG.txt').write_text(f'''MỚI-096 — ĐỒI BOSNIA / KIỂM TRA TUYÊN BỐ KIM TỰ THÁP — {C['display_duration']}

Kịch bản Anh {words} từ, khoảng {words/(T/60):.1f} từ/phút; 200 block lời dài 3–10 giây. Mười phần chung: 9×124+126 giây. Mở bằng một góc phiến đá trong 10 giây; câu hỏi chính trước 30 giây, phát hiện đầu trước hai phút; rehook 60–90 giây, một beat giới hạn bằng chứng ở cuối mỗi phần, cách nhau ít nhất 120 giây. Kết trả lời rồi một câu hỏi còn mở. Xem RETENTION_QA.json.
130 prompt / 13 TXT × 10. Timeline 128 cảnh: clip001 dùng10s;002–006 dùng4s/cảnh;007–127 dùng10s/cảnh;128 dùng2s.129–130 là hai dự phòng, không cộng vào thời lượng. Mỗi clip tạo10s; CSV gắn mọi ID lời chồng lấn. Block lời 3–10s độc lập với clip10s.
Ưu tiên đồi xanh, lớp đá, di tích nhỏ, mô hình vật lý ngoài trời. Không trẻ em, phòng thí nghiệm, chữ đọc được hoặc âm thanh. Mỗi prompt kết: “{silent}” Khi dựng, xóa âm clip và chỉ dùng voice Anh; không nhạc/SFX. Thiếu cảnh thì dùng video chuyển động liên quan, không ảnh đứng có chữ.
Mọi cảnh AI là minh họa/replica/mô hình, không footage xác thực, địa hình đo thật, hiện vật gốc, kết quả radar, hồ sơ khai quật hoặc bản phục dựng chính xác thành Visoki. Chú thích nguồn gốc minh họa khi xuất bản. Không dựng kim tự tháp khổng lồ như phát hiện có thật, tia năng lượng, căn phòng bí mật hoặc lực lượng xây kim tự tháp thời băng hà. Di tích quốc gia Visoki khác với tuyên bố kim tự tháp. Đọc nguồn và phạm vi đã kiểm chứng trước khi sản xuất.
Giữ16IDnam, gồm Andrew/NamMinh. Dùng backendonline khóa của Melo-Viet-Studio1.3.1 / MicrosoftEdge qua edge-tts; không GUIWindows hay modelMelo đa ngôn ngữ cục bộ. Không đổi pitch, cắt từ để ép thời lượng hoặc lấp im lặng dài. MỗiMP3 cần giải mã59.616.000mẫu mono48kHz=1.242s. Anh căn200block; bản nước ngoài chuyển thể10phần, không đồng bộ từng từ. SRTdịch theo phần cần chia nhỏ trước khi hiển thị. Chưa kiểm nghe/biên tập bản ngữ độc lập.
Chưa tạo footage, thumbnail hoặc MP4.\n''',encoding='utf-8')
(D/'README.md').write_text(f'''# MỚI-096 — Những ngọn đồi Bosnia — {C['display_duration']}

[Kịch bản Anh]({BASE}KICH_BAN_EN_{C['duration_label']}.txt) · [Tài liệu]({BASE}{PREFIX}_TAI_LIEU_{C['duration_label']}.zip) · [13 TXT prompt]({BASE}{PREFIX}_PROMPT_13_TXT.zip) · [5 tiêu đề/thumbnail]({BASE}5_TIEU_DE_VA_THUMBNAIL.txt)

Kịch bản mới {words} từ, {words/(T/60):.1f} từ/phút, 200 block lời 3–10 giây. Kiểm tra ba nhóm: hình dáng, vật liệu/phân tầng, dấu xây dựng và niên đại. Phân biệt đồi tự nhiên, di tích Visoki có thật và tuyên bố kim tự tháp chưa được chứng minh. Đã đọc cả nguồn khảo cổ lẫn các phần liên quan trong bài đề xuất năm2025; không dùng số đo của bên quảng bá như chứng cứ đã được độc lập xác nhận.

130 prompt/13TXT; timeline128cảnh:10+5×4+121×10+2=1.242s.129–130dự phòng. Hook một phiến đá10s; rehook60–90s; caveat cách≥120s. Xem RETENTION_QA.json, NGUON_KIEM_CHUNG.md và kế hoạch dựng. Toàn bộ cảnh ngoài trời, không trẻ em/lab/chữ/âm thanh/lời nói. Cảnh AI chỉ minh họa, không dữ liệu hoặc footage khảo cổ thật. Chưa tạo footage/thumbnail/MP4.

Giữ16IDgiọng nam, gồm Andrew/NamMinh qua backendonline khóaMelo-Viet-Studio1.3.1 /MicrosoftEdge. Tài liệu phát hành trước audio; chỉ báo đủ sau khi giải mã từngMP3đúng1.242s. Các bản nước ngoài chuyển thể10phần(9×124+126), không đồng bộ từng từ, chưa kiểm nghe bản ngữ độc lập.
''',encoding='utf-8')
for suffix,root,pattern in [(f'TAI_LIEU_{C["duration_label"]}',D,None),(f'PROMPT_{C["prompt_txt_files"]}_TXT',P,'*.txt')]:
 with zipfile.ZipFile(R/f'{PREFIX}_{suffix}.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(root.glob(pattern) if pattern else root.rglob('*')):
   if p.is_file():z.write(p,p.relative_to(root))
print(json.dumps(qa,ensure_ascii=False),flush=True)
