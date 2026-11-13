import csv,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def tc(t):return f'{t//60:02d}:{t%60:02d}'

def main():
 camera={int(n):text for n,text in (line.split('\t',1) for line in (ROOT/'prompts/camera-by-cue.tsv').read_text().splitlines())}
 assert len(camera)==100
 alias={4:3,5:3,7:8,11:10,12:3,14:13,19:18,23:22,26:25,29:28,30:28,31:10,32:15,
 37:33,43:42,45:44,46:35,47:39,50:49,54:48,56:55,57:48,58:36,59:36,62:61,63:2,
 66:65,69:68,70:64,71:41,73:72,75:9,76:60,77:65,79:78,80:78,84:83,88:86,90:86,
 91:65,92:48,93:48,94:89,96:95,99:97,101:41,103:100,105:104,107:106,108:78,109:48,
 110:41,111:36,112:106,114:49,115:113,117:106,118:106,119:1,120:48,121:2,122:81,
 123:65,124:44,125:60,126:16,127:3,128:113,129:1}
 # Cue 7 introduces the inhabited setting before its detailed model appears at 8.
 alias[7]=3
 alias={k:v for k,v in alias.items() if k not in camera}
 assert set(camera)|set(alias)==set(range(1,130)) and not set(camera)&set(alias)
 assert all(v in camera and v<k for k,v in alias.items()),[(k,v) for k,v in alias.items() if v>=k]
 ids={cue:i+1 for i,cue in enumerate(sorted(camera))}
 en=json.loads((ROOT/'scripts/en.json').read_text());vi=json.loads((ROOT/'scripts/vi.json').read_text())
 timeline=[]
 for n in range(1,130):
  first=alias.get(n,n);timeline.append(dict(slot=n,start_seconds=(n-1)*10,duration_seconds=10,prompt=ids[first],first_use_cue=first,reuse=n!=first))
 timeline.append(dict(slot=130,start_seconds=1290,duration_seconds=2,prompt=ids[1],first_use_cue=1,reuse=True,hold_final_frame=True))
 assert sum(x['duration_seconds'] for x in timeline)==1292 and sum(x['reuse'] for x in timeline)==30
 guard=('VIDEO KHÔNG CÓ HÌNH TRẺ EM; ABSOLUTELY NO CHILDREN, BABIES OR TEENAGERS anywhere; all people must be visibly adult, aged 25 or older. '
        'VIDEO KHÔNG CÓ ÂM THANH, KHÔNG LỜI NÓI; SILENT VIDEO: NO AUDIO, NO SPEECH, NO SPOKEN WORDS, NO MUSIC, NO SOUND EFFECTS, NO LIP-SYNC. '
        'No text, subtitles, logos, watermarks, fantasy architecture, invented inscriptions, miniature human figures, childlike statues or staged sacred ceremonies. '
        'Scientific models are explanatory illustrations, not exact surveys, excavations or footage of ancient events. No unsafe access or alteration of heritage. ')
 prompts=[]
 for cue in sorted(camera):
  n=ids[cue];uses=', '.join(f"{x['slot']:03d}" for x in timeline if x['prompt']==n)
  prompts.append(f'{n}. Generate one coherent 10-second 16:9 documentary-inspired video clip, suitable for 4K. SETTING: Angkor and its wider water landscape near Siem Reap, Cambodia. NARRATIVE CONTEXT ONLY, never display or speak: {en[cue-1]["text"]} CAMERA AND ACTION: {camera[cue]} Establish for 2 seconds, reveal for 6 seconds, settle for 2 seconds. Restrained camera movement, plausible scale, natural materials and physically consistent water. {guard}Generate once; reuse according to timeline slots {uses}.')
 for i in range(10):(ROOT/f'prompts/prompt-{i+1:02d}.txt').write_text('\n\n'.join(prompts[i*10:(i+1)*10])+'\n',encoding='utf-8-sig')
 plan=dict(episode=85,generated_clip_seconds=10,unique_prompts=100,reused_slots=30,timeline_slots=130,spoken_cues=129,closing_hold_seconds=2,total_seconds=1292,canonical_cues=sorted(camera),timeline=timeline)
 (ROOT/'shot-reuse-map.json').write_text(json.dumps(plan,indent=2)+'\n')
 lines=['# Bảng dựng đủ 21:32 — tập 85 Angkor','','129 đoạn × 10 giây + 2 giây giữ khung hình kết = 1.292 giây. **100 clip tạo mới**, mỗi clip 10 giây; **29 đoạn dùng lại** đủ 10 giây và **1 ô giữ khung hình cuối 2 giây**. Tổng 1.000 + 290 + 2 = 1.292 giây. Bối cảnh lặp được gắn lại mã clip, không tạo thêm prompt trùng.','','| Ô | Từ–đến | Mã clip / prompt | Thao tác |','|---|---|---|---|']
 with (ROOT/'scene-voice-edit.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['slot','start','end','seconds','prompt','action','voice_en','voice_vi'])
  for x in timeline:
   n=x['slot'];start=x['start_seconds'];duration=x['duration_seconds'];action='Giữ khung hình cuối 2 giây' if x.get('hold_final_frame') else ('Dùng lại' if x['reuse'] else 'Tạo một lần')
   lines.append(f'| {n:03d} | {tc(start)}–{tc(start+duration)} | {x["prompt"]:02d} | {action} |')
   w.writerow([n,tc(start),tc(start+duration),duration,x['prompt'],action,en[n-1]['text'] if n<=129 else '',vi[n-1]['text'] if n<=129 else ''])
 (ROOT/'BANG-TINH-130-DOAN.md').write_text('\n'.join(lines)+'\n')
 with zipfile.ZipFile(ROOT/'100-prompts-10-txt-10s.zip','w',zipfile.ZIP_DEFLATED) as z:
  for i in range(1,11):p=ROOT/f'prompts/prompt-{i:02d}.txt';z.write(p,p.name)
 (ROOT/'60-prompts-6-txt-10s.zip').unlink(missing_ok=True)
 state=json.loads((ROOT/'PRODUCTION_STATE.json').read_text());state.update(unique_generated_clips=100,prompt_count=100,prompt_files=10,reused_slots=30,reused_full_slots=29,closing_hold_seconds=2)
 (ROOT/'PRODUCTION_STATE.json').write_text(json.dumps(state,indent=2)+'\n')
 print('100 unique prompts; 10 TXT; 129 ten-second slots and 2-second closing hold; exact 1292 seconds.')

if __name__=='__main__':main()
