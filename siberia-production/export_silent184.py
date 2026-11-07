"""Export a voice-verified, camera-directed 184 shot plan; no Muse calls."""
from pathlib import Path
import argparse,csv,hashlib,html,json,math,re,shutil,subprocess,zipfile
from camera_directing_184 import choose_camera,build_prompt

BASE=Path(__file__).resolve().parent
VOICE_SHA='31ddc272cb789f24e5a383159c5674918bc3562e1c9da088f3f28385ed943c68'
CHOICES={2:[0,1],3:[0,2],10:[0,2,3],11:[0,2,3],12:[0,2,3],22:[0,2,3],24:[0,1,2],26:[0,1,2],27:[0,2,3],30:[0,2,3],32:[0,2,3],33:[0,1,2],34:[0,1,3],35:[0,2,3],36:[0,1,2],37:[0,2,3],38:[0,2],40:[0,2,3],43:[0,2,3],54:[0,1,2],55:[0,1,2],56:[0,2,3],57:[0,2,3],58:[0,2,3],59:[0,2]}
BEATS_VI={
 'aerial_oblique':'0–2s: thấy rõ toàn bộ chủ thể; 2–8s: lướt ngang khoảng 5% bề ngang khung; 8–10s: giảm tốc và giữ khung.',
 'aerial_push':'0–2s: có ngay toàn cảnh; 2–8s: tiến nhẹ, thay đổi kích thước hình dưới 8%; 8–10s: giữ ổn định.',
 'aerial_pullback':'0–2s: chủ thể hiện rõ; 2–8s: lùi máy chậm để mở rộng không gian; 8–10s: giữ đại cảnh.',
 'topdown':'0–2s: toàn bộ cấu trúc có sẵn trong khung; 2–8s: trôi ngang tối đa 5% khung, không xoay; 8–10s: đứng khung.',
 'wide_eye':'0–2s: đọc rõ tiền cảnh và hậu cảnh; 2–8s: tiến máy nhẹ; 8–10s: dừng êm.',
 'low_landscape':'0–2s: thấy ngay chủ thể và bối cảnh; 2–8s: trượt ngang thấp chậm; 8–10s: giữ rõ chủ thể.',
 'medium_lateral':'0–2s: đặt chủ thể rõ trong bố cục; 2–8s: trượt ngang chậm, không lia gấp; 8–10s: giữ góc cuối.',
 'low_rock':'0–2s: thấy khối đá cùng điểm tựa; 2–8s: dịch ngang rất ít để lộ mặt tiếp xúc; 8–10s: giữ. Khối đá đứng yên.',
 'telephoto':'0–2s: nhận ra chủ thể; 2–8s: lia tối đa 3 độ hoặc đứng máy; 8–10s: giữ, không zoom.',
 'close_texture':'0–2s: chi tiết chính nét ngay; 2–8s: trượt dưới 5% bề ngang khung; 8–10s: giữ nét và kết cấu.',
 'macro':'0–2s: chi tiết chính hiện rõ; 2–8s: chuyển nét nhẹ trên cùng bề mặt, không biến hình; 8–10s: khóa nét.',
 'locked_wide':'0–2s: thấy rõ chủ thể; 2–8s: máy cố định, chỉ mây/nước/cây chuyển động tự nhiên; 8–10s: giữ nguyên khung.',
 'reconstruction_eye':'0–2s: thấy ngay đối tượng tái dựng; 2–8s: tiến nhẹ, kiến trúc và bố cục ổn định; 8–10s: giữ.',
 'schematic':'0–2s: thấy các thành phần; 2–8s: minh họa đúng một cơ chế; 8–10s: giữ trạng thái. Máy trực giao cố định, không số liệu giả.'}

def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sm(ms):
 sec,milli=divmod(ms,1000);minute,sec=divmod(sec,60);hour,minute=divmod(minute,60)
 return f'{hour:02}:{minute:02}:{sec:02}.{milli:03}'
def sf(frame):
 sec,n=divmod(frame,30);minute,sec=divmod(sec,60);hour,minute=divmod(minute,60)
 return f'{hour:02}:{minute:02}:{sec:02}:{n:02}'
def millis(s):
 h,m,s=s.replace(',','.').split(':');sec,ms=s.split('.')
 return ((int(h)*60+int(m))*60+int(sec))*1000+int(ms)
def norm(s):return ' '.join(html.unescape(s).split())
def location(subject,chapter,cid):
 s=subject.lower()
 for words,place in [
  (['chara','kodar'],'Chara Sands, a localized dune field beside taiga in the Kodar mountain basin, Siberia'),
  (['baikal','ice ring','dark ring'],'Lake Baikal in winter, Siberia'),
  (['lena','pillars'],'Lena Pillars along the Lena River, Siberia'),
  (['putorana'],'Putorana Plateau, northern Central Siberia'),
  (['por-bazhyn','ter e-khol','tere-khol'],'Por-Bazhyn ruins on an island in Lake Tere-Khol, Tuva'),
  (['patomskiy'],'Patomskiy raised rubble cone in forested Irkutsk region, Siberia'),
  (['ergaki','hanging stone','sleeping sayan'],'Ergaki mountains, southern Siberia; granite ridges and Lake Raduzhnoye'),
  (['batagaika','thaw slump','headwall'],'Batagaika thaw slump in northeastern Siberia'),
  (['belukha','altai','teletskoye','ukok'],'Altai mountain region, Siberia; Belukha massif where specified'),
  (['vasyugan','west siberian','wetland','peatland','mire','peat soil','fibrous peat'],'Great Vasyugan Mire region in the West Siberian Plain'),
  (['tunguska','airblast','atmospheric flash','atmospheric fragmentation'],'Tunguska region, Siberia; historical scenes refer to the 1908 atmospheric event')]:
  if any(w in s for w in words):return place
 if cid==8 and 'lake ice' in s:return 'Lake Baikal in winter, Siberia'
 if cid==18 and 'plateau' in s:return 'Putorana Plateau, northern Central Siberia'
 return {'Opening':'Siberian wilderness','Closing':'Siberian wilderness'}.get(chapter,chapter+', Siberia')

def export(out,proof):
 if out.exists():shutil.rmtree(out)
 out.mkdir(parents=True);folder=out/'MUSE_184_SILENT_25m36';folder.mkdir()
 master=json.loads((BASE/'master_timeline.json').read_text(encoding='utf-8'))
 motifs=json.loads((BASE/'silent184_motifs.json').read_text(encoding='utf-8'))
 vi=json.loads((BASE/'curated_cues.json').read_text(encoding='utf-8'))['vi']
 if proof is None:
  proof=out/'verified-voice';proof.mkdir()
  subprocess.run(['gh','release','download','siberia-2536-production-v1','--repo','seotro95/seotro','--pattern','en.srt','--pattern','en-report.json','--dir',str(proof),'--clobber'],check=True)
 report=json.loads((proof/'en-report.json').read_text(encoding='utf-8'))
 assert report['sync_ok'] and report['duration_verified'] and report['audio_seconds']==1536
 assert report['duration_report']['sample_frames']==73728000 and report['audio_sha256']==VOICE_SHA
 release=json.loads(subprocess.check_output(['gh','api','repos/seotro95/seotro/releases/436895553'],text=True))
 asset=next(a for a in release['assets'] if a['name']=='en.wav')
 assert asset['digest']=='sha256:'+VOICE_SHA
 blocks=re.split(r'\n\s*\n',(proof/'en.srt').read_text(encoding='utf-8-sig').strip())
 assert len(blocks)==len(master['cues'])==59
 for block,cue,measured in zip(blocks,master['cues'],report['sync_report']['cues']):
  lines=block.splitlines();a,b=lines[1].split(' --> ')
  assert int(lines[0])==cue['id'] and millis(a)==cue['start_ms'] and millis(b)==cue['end_ms']
  assert norm(' '.join(lines[2:]))==norm(cue['text'])
  assert measured['start_frame']==cue['start_ms']*48 and measured['end_frame']==cue['end_ms']*48
 shots=[];rounding=0;cue_based=0
 for cue in master['cues']:
  cid=cue['id'];n=math.ceil((cue['end_ms']-cue['start_ms'])/10000);cue_based+=n
  if cid==1:n=4
  options=motifs[str(cid)]
  selected=CHOICES.get(cid,list(range(n)) if n==len(options) else ([0,1,len(options)-1] if n==3 else [0,len(options)-1]))
  assert len(selected)==n and len(set(selected))==n,(cid,n,selected)
  start=round(cue['start_ms']*.03);end=round(cue['end_ms']*.03)
  rounding=max(rounding,abs(start/30*1000-cue['start_ms']),abs(end/30*1000-cue['end_ms']))
  bounds=[round(start+(end-start)*i/n) for i in range(n+1)]
  if cid==1:bounds=[0,78,147,249,414]
  for j,index in enumerate(selected):
   subject=options[index]
   kind='schematic' if subject.startswith('DIAGRAM') else ('historical reconstruction' if subject.startswith('RECONSTRUCTION') else 'AI geography illustration')
   camera=choose_camera(subject,kind,cid,j,n);camera['beats_0_to_10_vi']=BEATS_VI[camera['profile']]
   frames=bounds[j+1]-bounds[j];source_in=min(6,max(0,300-frames-8));sid=len(shots)+1
   s={'id':sid,'filename':f'{sid:04}.mp4','batch':(sid-1)//10+1,'slot':(sid-1)%10+1,
    'cue_id':cid,'chapter':cue['chapter'],'voice_start_ms':cue['start_ms'],'voice_end_ms':cue['end_ms'],
    'start_frame':bounds[j],'end_frame':bounds[j+1],'frames':frames,'source_in_frames':source_in,
    'source_out_frames':source_in+frames,'requested_clip_seconds':10,'kind':kind,'subject':subject,
    'camera':camera,'incoming_transition':'cut','audio_requested':False,
    'prompt':build_prompt(subject+'; location context: '+location(subject,cue['chapter'],cid),kind,camera)}
   shots.append(s)
 assert cue_based==182 and len(shots)==184 and shots[-1]['end_frame']==46080 and rounding<=1000/60+1e-6
 assert shots[0]['start_frame']==0 and all(a['end_frame']==b['start_frame'] for a,b in zip(shots,shots[1:]))
 assert all(0<s['frames']<=300 and s['source_out_frames']<=300 for s in shots)
 assert len({s['prompt'] for s in shots})==184 and all('ABSOLUTELY SILENT' in s['prompt'] for s in shots)
 plan={'version':1,'title':master['title'],'fps':30,'duration_seconds':1536,'total_frames':46080,'requested_source_seconds':1840,
  'trimmed_source_seconds':304,'voice_sha256':VOICE_SHA,'shot_count':184,'audio_requested':False,'shots':shots}
 dump(folder/'shot_plan_184.json',plan)
 pure='\n\n'.join(s['prompt'] for s in shots)+'\n';(out/'MUSE_184_SILENT_PROMPTS.txt').write_text(pure,encoding='utf-8')
 header=f'''184 CẢNH IM LẶNG — SIBERIA 25:36 — KÈM GÓC QUAY CHO TỪNG CẢNH

25:36 = 1.536 giây. Tối thiểu lý thuyết: 154 clip 10 giây.
Kế hoạch này: 184 clip để tách theo 59 đoạn voice và bốn hình mở đầu.
Tổng nguồn: 30:40. Cắt bỏ 5:04 để dùng đúng 25:36 / 46.080 frame ở 30 fps.
184 prompt này thay bộ 227 cảnh khi dùng quy trình hiện tại.

Voice chuẩn: en.wav — SHA-256 {VOICE_SHA}.
MỐC VOICE = giờ:phút:giây.mili giây. MỐC DỰNG = giờ:phút:giây:frame ở 30 fps.
MỐC DỰNG kết thúc là điểm loại trừ: clip sau bắt đầu ngay tại frame đó.
Mỗi prompt là một máy quay liên tục trong 10 giây; không đổi góc giữa clip.
Góc máy và tiêu cự là yêu cầu sáng tạo; không phải thông số đo từ tư liệu gốc.
Mốc lời đã đối chiếu 59 đoạn; chưa căn từng từ. Các cảnh ngắn lấy đúng phần nguồn được ghi.
Các mốc 2,60 / 4,90 / 8,30 giây ở mở đầu dựa trên kiểm tra lời nhận dạng tự động.
Các cảnh tái dựng/sơ đồ phải gắn nhãn phù hợp trong phần mềm dựng, không yêu cầu model tự vẽ chữ.

'''
 story=[header];rows=[]
 for cue in master['cues']:
  story.extend(['='*76,f"ĐOẠN VOICE {cue['id']:02} — {cue['chapter']}",f"VOICE: {sm(cue['start_ms'])} → {sm(cue['end_ms'])}",'LỜI ANH:',cue['text'],'Ý NGHĨA VIỆT:',vi[str(cue['id'])],''])
  for s in [x for x in shots if x['cue_id']==cue['id']]:
   c=s['camera'];lens=f"{c['lens_equivalent_mm']} mm tương đương" if c['lens_equivalent_mm'] else 'Trực giao; không giả lập ống kính'
   story.extend([f"CẢNH {s['id']:04} | BỘ {s['batch']:02} / Ô {s['slot']:02} | LƯU {s['filename']}",
    'HÌNH: '+s['subject'],'GÓC QUAY: '+c['shot_and_angle_vi']+' | '+lens,
    'DIỄN TIẾN 10 GIÂY: '+c['beats_0_to_10_vi'],
    f"DỰNG: {sf(s['start_frame'])} → {sf(s['end_frame'])}; dùng {s['frames']/30:.6f}s ({s['frames']} frame).",
    f"CẮT TRONG NGUỒN: {s['source_in_frames']/30:.6f}s → {s['source_out_frames']/30:.6f}s.",
    'CHUYỂN VÀO: cắt thẳng đúng mốc; tắt toàn bộ âm thanh clip.','PROMPT:',s['prompt'],''])
   rows.append({'shot':s['id'],'filename':s['filename'],'batch':s['batch'],'slot':s['slot'],'cue':cue['id'],'chapter':cue['chapter'],
    'voice_start':sm(cue['start_ms']),'voice_end':sm(cue['end_ms']),'voice_english':cue['text'],'meaning_vietnamese':vi[str(cue['id'])],
    'timeline_start_30fps':sf(s['start_frame']),'timeline_end_30fps':sf(s['end_frame']),'used_frames':s['frames'],'used_seconds':f"{s['frames']/30:.6f}",
    'source_in_seconds':f"{s['source_in_frames']/30:.6f}",'source_out_seconds':f"{s['source_out_frames']/30:.6f}",
    'subject':s['subject'],'camera_vi':c['shot_and_angle_vi'],'lens_mm':c['lens_equivalent_mm'],'downward_angle_deg':c['downward_view_degrees'],
    'camera_movement':c['movement_en'],'beats_vi':c['beats_0_to_10_vi'],'kind':s['kind'],'transition':'cut','audio':'off','prompt':s['prompt']})
 (out/'MUSE_184_STORYBOARD_VI.txt').write_text('\n'.join(story)+'\n',encoding='utf-8')
 with (out/'MUSE_184_TIMELINE.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 (folder/'batches').mkdir();template=json.loads((BASE/'kit/muse-projects/video-01.json').read_text(encoding='utf-8'))
 for offset in range(0,184,10):
  group=shots[offset:offset+10];num=offset//10+1
  (folder/'batches'/f'video-{num:02}.txt').write_text('\n\n'.join(s['prompt'] for s in group)+'\n',encoding='utf-8')
  project={'version':1,'settings':template['settings'],'scenes':[{'prompt':s['prompt'],'enabled':True} for s in group]+[{'prompt':'','enabled':False} for _ in range(10-len(group))]}
  assert len(project['scenes'])==10
  dump(folder/'batches'/f'video-{num:02}.json',project)
 qa={'prompt_count':184,'batches':19,'last_batch_enabled_slots':4,'cue_count':59,'theoretical_minimum_10s_clips':154,
  'minimum_if_no_clip_crosses_a_cue':182,'opening_extra_clips':2,'raw_seconds':1840,'unused_source_seconds':304,
  'target_seconds':1536,'fps':30,'total_frames':46080,'published_voice_sha256':VOICE_SHA,'published_wav_digest_matches_report':True,
  'srt_all_cue_text_and_times_match_master':True,'maximum_visual_cue_rounding_ms':rounding,'word_level_alignment_claimed':False,
  'camera_profile_counts':{k:sum(s['camera']['profile']==k for s in shots) for k in sorted({s['camera']['profile'] for s in shots})},
  'all_prompts_request_no_audio_track':True,'audio_removal_tool_included':True,'camera_angles_are_creative_requests':True,
  'muse_clips_generated':False,'completed_video_included':False}
 dump(out/'MUSE_184_QA.json',qa)
 for name in ['MUSE_184_SILENT_PROMPTS.txt','MUSE_184_STORYBOARD_VI.txt','MUSE_184_TIMELINE.csv','MUSE_184_QA.json']:
  shutil.copyfile(out/name,folder/name)
 for name in ['en.srt','en-report.json']:shutil.copyfile(proof/name,folder/name)
 for p in (BASE/'silent184_helpers').iterdir():
  if p.is_file():shutil.copyfile(p,folder/p.name)
 core=(BASE/'kit/production.mjs').read_text(encoding='utf-8').split('export function localURL')[0]
 (folder/'ffmpeg_tools.mjs').write_text(core,encoding='utf-8')
 shutil.copyfile(BASE/'SILENT184_README_VI.md',folder/'README_VI.md')
 shutil.copyfile(BASE/'SILENT184_README_VI.md',out/'MUSE_184_README_VI.md')
 shutil.copyfile(BASE/'EN_script.txt',folder/'EN_script.txt') if (BASE/'EN_script.txt').exists() else None
 (folder/'clips').mkdir()
 internal=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(folder).as_posix()+'\n' for p in sorted(folder.rglob('*')) if p.is_file())
 (folder/'CONTENTS_SHA256SUMS.txt').write_text(internal,encoding='utf-8')
 archive=out/'MUSE_184_SILENT_25m36.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(folder.rglob('*')):
   if p.is_file():z.write(p,Path(folder.name)/p.relative_to(folder))
 files=[p for p in sorted(out.iterdir()) if p.is_file()]
 (out/'MUSE_184_SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files),encoding='utf-8')
 print(json.dumps(qa,ensure_ascii=False))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('silent184-delivery'));p.add_argument('--voice-proof',type=Path)
 a=p.parse_args();export(a.out,a.voice_proof)
