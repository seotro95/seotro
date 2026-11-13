import csv,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def ts(s):return f'{s//60:02d}:{s%60:02d}'
def main():
 r=ROOT;m=json.loads((r/'shot-reuse-map.json').read_text());en=json.loads((r/'scripts/en.json').read_text());vi=json.loads((r/'scripts/vi.json').read_text())
 cameras={int(n):v for n,v in (l.split('\t',1) for l in (r/'prompts/camera-by-cue.tsv').read_text().splitlines())}
 assert set(cameras)==set(m['canonical_cues'])
 prompts=[]
 for i,n in enumerate(m['canonical_cues'],1):
  uses=[x['slot'] for x in m['timeline'] if x['prompt']==i]
  p=(f'{i}. Generate one coherent 10-second 16:9 documentary-inspired video clip, suitable for 4K. SETTING: Flores, East Nusa Tenggara, eastern Indonesia; plausible limestone caves, volcanic ridges and contemporary island communities. '
     f'NARRATIVE CONTEXT ONLY, never display or speak: {en[n-1]["text"]} CAMERA AND ACTION: {cameras[n]} '
     'Establish for 2 seconds, reveal for 6 seconds, settle for 2 seconds. Use realistic scale, restrained motion and physical consistency. Models are illustrative, not discoveries or exact surveys. '
     'VIDEO KHÔNG CÓ HÌNH TRẺ EM; ABSOLUTELY NO CHILDREN, BABIES OR TEENAGERS anywhere; all people must be visibly adult, aged 25 or older. '
     'VIDEO KHÔNG CÓ ÂM THANH, KHÔNG LỜI NÓI; SILENT VIDEO: NO AUDIO, NO SPEECH, NO SPOKEN WORDS, NO MUSIC, NO SOUND EFFECTS, NO LIP-SYNC. '
     'No text, subtitles, logos, watermarks, fantasy wildlife, invented ruins, active eruption, unsafe access or staged ceremonies. No prehistoric human reenactments, miniature people, hominin body figures, recognizable human remains, or childlike silhouettes. Scientific visuals must use neutral objects, abstract models and clearly modern adults. No instantaneous changes to volcanic-lake colors. Generate once; reuse the existing clip at slots '+', '.join(f'{x:03d}' for x in uses)+'.')
  prompts.append(p)
 for b in range(6):(r/f'prompts/prompt-{b+1:02d}.txt').write_text('\n\n'.join(prompts[b*10:b*10+10])+'\n',encoding='utf-8-sig')
 with zipfile.ZipFile(r/'60-prompts-6-txt-10s.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted((r/'prompts').glob('prompt-*.txt')):z.write(p,p.name)
 with (r/'scene-voice-edit.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['slot','start','end','seconds','prompt','action','voice_en','voice_vi'])
  for x in m['timeline']:
   n=x['slot'];w.writerow([n,ts(x['start_seconds']),ts(x['start_seconds']+10),10,x['prompt'],'REUSE EXISTING CLIP' if x['reuse'] else 'GENERATE ONCE',en[n-1]['text'],vi[n-1]['text']])
 lines=['# Bảng tính đủ 22:00 — mỗi clip 10 giây','','22 phút = 1.320 giây = 132 vị trí × 10 giây. **60 prompt mới** tạo 600 giây hình gốc; **72 vị trí dùng lại** thêm 720 giây. Không bỏ lời hoặc rút thời lượng khi bỏ prompt trùng.','','Mỗi prompt chỉ tạo một clip 10 giây. Có 6 TXT, mỗi tệp 10 prompt, không thêm cảnh dự phòng.','','| Vị trí | Từ–đến | Prompt tạo clip | Thao tác |','|---|---|---|---|']
 for x in m['timeline']:lines.append(f'| {x["slot"]:03d} | {ts(x["start_seconds"])}–{ts(x["start_seconds"]+10)} | {x["prompt"]:02d} | '+('Dùng lại' if x['reuse'] else 'Tạo một lần')+' |')
 (r/'BANG-TINH-132-DOAN.md').write_text('\n'.join(lines)+'\n')
 state=json.loads((r/'PRODUCTION_STATE.json').read_text());state.update(prompt_count=60,prompt_files=6,generated_clip_seconds=10,main_scenes=132,reused_slots=72,unique_generated_clips=60);(r/'PRODUCTION_STATE.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
 print('60 unique prompts; 132 slots; 72 reuses; exact 1320 seconds')
if __name__=='__main__':main()
