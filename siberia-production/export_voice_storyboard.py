"""Pair every planned Muse shot with the verified published English cue timeline."""
from pathlib import Path
import csv,hashlib,html,json,os,re,shutil,subprocess,zipfile

def export_storyboard(base,out,folder,plan):
 base,out,folder=map(Path,[base,out,folder]);repo=os.environ.get('GITHUB_REPOSITORY','seotro95/seotro')
 proof=out/'voice-verification';proof.mkdir(exist_ok=True)
 subprocess.run(['gh','release','download','siberia-2536-production-v1','--repo',repo,
  '--pattern','en.srt','--pattern','en-report.json','--dir',str(proof),'--clobber'],check=True)
 master=json.loads((base/'master_timeline.json').read_text(encoding='utf-8'))
 vi=json.loads((base/'curated_cues.json').read_text(encoding='utf-8'))['vi']
 report=json.loads((proof/'en-report.json').read_text(encoding='utf-8'))
 assert report['sync_ok'] and report['duration_verified'] and report['audio_seconds']==1536
 assert report['duration_report']['sample_frames']==73728000
 release=json.loads(subprocess.check_output(['gh','api','repos/'+repo+'/releases/436895553'],text=True))
 assets={a['name']:a for a in release['assets']}
 assert assets['en.wav']['digest']=='sha256:'+report['audio_sha256'],'The uploaded WAV must match its verification report'
 def ms(s):
  h,m,rest=s.replace(',','.').split(':');sec,milli=rest.split('.')
  return ((int(h)*60+int(m))*60+int(sec))*1000+int(milli)
 def normal(s):return ' '.join(html.unescape(s).split())
 blocks=re.split(r'\n\s*\n',(proof/'en.srt').read_text(encoding='utf-8-sig').strip())
 assert len(blocks)==len(master['cues'])==59
 for block,cue,measured in zip(blocks,master['cues'],report['sync_report']['cues']):
  lines=block.splitlines();a,b=lines[1].split(' --> ')
  assert int(lines[0])==cue['id'] and ms(a)==cue['start_ms'] and ms(b)==cue['end_ms']
  assert normal(' '.join(lines[2:]))==normal(cue['text']),(cue['id'],'Different narration text')
  assert measured['start_frame']==cue['start_ms']*48 and measured['end_frame']==cue['end_ms']*48
 def stamp_ms(n):
  sec,milli=divmod(n,1000);minute,sec=divmod(sec,60);hour,minute=divmod(minute,60)
  return f'{hour:02}:{minute:02}:{sec:02}.{milli:03}'
 def stamp_frame(n):
  sec,frame=divmod(n,30);minute,sec=divmod(sec,60);hour,minute=divmod(minute,60)
  return f'{hour:02}:{minute:02}:{sec:02}:{frame:02}'
 shots=plan['shots'];assert len(shots)==227 and shots[0]['start_frame']==0 and shots[-1]['end_frame']==46080
 assert all(a['end_frame']==b['start_frame'] for a,b in zip(shots,shots[1:]))
 heading=f'''MUSE — STORYBOARD THEO VOICE ANH 25:36

Bản lời đã đối chiếu: en.srt trong GitHub Release của chủ kho.
Bản giọng chuẩn: en.wav, SHA-256 {report['audio_sha256']}.
Cũng dùng được với Siberia_EN_FINAL_MIX_25m36.wav: bản phối dùng cùng giọng và cùng mốc.

227 cảnh / 23 bộ / 59 đoạn voice / 46.080 frame ở 30 fps / 25:36.
Muse: Omni 1.1 Flash; Video từ văn bản; 16:9; yêu cầu 1080p; 10 giây mỗi clip.

MỐC VOICE là giờ:phút:giây.mili giây. MỐC DỰNG là giờ:phút:giây:frame, timeline 30 fps.
Tên lưu gợi ý: 0001.mp4 đến 0227.mp4. Trong Muse, dán riêng phần PROMPT của từng cảnh.
Tệp batches/video-01.txt đến video-23.txt là các prompt thuần, mỗi đoạn ứng với một ô Muse.

Đồng bộ được kiểm tra theo 59 đoạn lời. Các điểm cắt hình được lập ở lưới 30 fps; đây chưa phải căn từng từ.
Mỗi clip sinh 10 giây có phần dư để cắt và làm chuyển cảnh. Đặt clip theo MỐC DỰNG và độ dài ghi bên dưới.

'''
 text=[heading];rows=[];maximum_rounding=0
 for cue in master['cues']:
  group=[s for s in shots if s['cue_id']==cue['id']];assert group
  maximum_rounding=max(maximum_rounding,abs(group[0]['start_frame']/30*1000-cue['start_ms']),abs(group[-1]['end_frame']/30*1000-cue['end_ms']))
  text.extend(['='*76,f"ĐOẠN VOICE {cue['id']:02} — {cue['chapter']}",
   f"MỐC VOICE: {stamp_ms(cue['start_ms'])} → {stamp_ms(cue['end_ms'])}",
   'VOICE ENGLISH:',cue['text'],'Ý NGHĨA TIẾNG VIỆT:',vi[str(cue['id'])],''])
  for s in group:
   number=s['id'];batch=(number-1)//10+1;slot=(number-1)%10+1
   start,end=stamp_frame(s['start_frame']),stamp_frame(s['end_frame'])
   duration=s['frames']/30;source_out=s['source_in_seconds']+duration
   text.extend([f"CẢNH {number:04} | Bộ {batch:02}, ô {slot:02} | {s['kind']}",
    f'MỐC DỰNG: {start} → {end}',
    f"TẠO: 10 giây. DÙNG: {duration:.6f} giây ({s['frames']} frame).",
    f"ĐIỂM CẮT TRONG CLIP NGUỒN: {s['source_in_seconds']:.6f} → {source_out:.6f} giây.",
    f"CHUYỂN CẢNH VÀO: {s['transition']}",'PROMPT:',s['prompt'],''])
   rows.append({'shot_id':number,'suggested_filename':f'{number:04}.mp4','batch':batch,'muse_slot':slot,
    'voice_cue':cue['id'],'chapter':cue['chapter'],'voice_start':stamp_ms(cue['start_ms']),
    'voice_end':stamp_ms(cue['end_ms']),'voice_english':cue['text'],'meaning_vietnamese':vi[str(cue['id'])],
    'video_start_30fps':start,'video_end_30fps':end,'used_frames':s['frames'],'used_seconds':f'{duration:.6f}',
    'requested_clip_seconds':10,'source_in_seconds':f"{s['source_in_seconds']:.6f}",
    'source_out_seconds':f'{source_out:.6f}','incoming_transition':s['transition'],'visual_kind':s['kind'],'prompt':s['prompt']})
 storyboard=out/'MUSE_THEO_VOICE_25m36.txt';storyboard.write_text('\n'.join(text)+'\n',encoding='utf-8')
 csv_path=out/'VOICE_SHOT_TIMELINE.csv'
 with csv_path.open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
 assert maximum_rounding<=1000/60+1e-6
 qa={'verified_voice_cues':59,'planned_shots':227,'batch_count':23,'fps':30,'total_frames':46080,'duration_seconds':1536,
  'published_english_wav_sha256':report['audio_sha256'],'uploaded_wav_digest_matches_report':True,
  'published_srt_text_and_times_match_master':True,'maximum_visual_boundary_rounding_ms':maximum_rounding,
  'intro_edit_points_seconds':plan.get('intro_edit_points_seconds'),
  'intro_visual_sequence':['Chara Sands','Por-Bazhyn','Lake Baikal ice ring','Siberian landscape'],
  'word_level_alignment_claimed':False,'muse_media_created':False,'completed_video_included':False}
 (out/'VOICE_STORYBOARD_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
 for src in [storyboard,csv_path,out/'VOICE_STORYBOARD_QA.json',proof/'en.srt',proof/'en-report.json']:
  shutil.copyfile(src,folder/src.name)
 extra='''\n## Dựng theo đúng bản voice đã chốt

Mở `MUSE_THEO_VOICE_25m36.txt`: mỗi đoạn có lời Anh thực tế, ý nghĩa Việt và các cảnh cần tạo. `VOICE_SHOT_TIMELINE.csv` có một dòng cho từng cảnh, đủ tên lưu, số bộ/ô Muse, mốc voice, mốc dựng ở 30 fps, độ dài cần dùng và điểm cắt clip nguồn. `en.srt` là bản mốc voice đã đối chiếu với master.

Dựng theo độ dài trong bảng để giữ 25:36. Với dissolve, dùng phần media dư làm handle và giữ nguyên các mốc cắt trên timeline. Những con số này là kế hoạch dựng; clip tạo sinh vẫn cần được xem lại để bảo đảm hình minh họa đúng phần lời đang đọc.
'''
 with (folder/'README_VI.md').open('a',encoding='utf-8') as f:f.write(extra)
 archive=out/'MUSE_THEO_VOICE_25m36.zip'
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(folder.rglob('*')):
   if p.is_file():z.write(p,Path('MUSE_THEO_VOICE_25m36')/p.relative_to(folder))
 return [storyboard.name,csv_path.name,'VOICE_STORYBOARD_QA.json',archive.name]
