"""Verify the 17 actual MP3s, scripts and updated 100-prompt delivery."""
import csv,hashlib,json,os,re,subprocess,zipfile
from pathlib import Path
import numpy as np
import soundfile as sf

ROOT=Path(__file__).resolve().parents[1]
SECONDS=1292
FRAMES=31008000
CUES=129

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()

def save(path,data):Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

def main():
 profiles=json.loads((ROOT/'VOICE_PROFILES.json').read_text());voices={x['language']:x for x in profiles['profiles']}
 previous={x['language']:x['voice_id'] for x in json.loads(Path('/workspace/episode-040-flores/VOICE_PROFILES.json').read_text())['profiles']}
 assert {c:v['voice_id'] for c,v in voices.items()}==previous
 assert len(voices)==17 and sum(x['gender']=='Male' for x in voices.values())==16
 assert voices['en']['voice_id']=='en-US-AndrewNeural' and voices['vi']['voice_id']=='vi-VN-NamMinhNeural'
 assert voices['hmn']['voice_id']=='hmong-female-3' and voices['hmn']['gender']=='Female'
 assert all(v['target_seconds']==SECONDS for v in voices.values())
 plan=json.loads((ROOT/'shot-reuse-map.json').read_text());timeline=plan['timeline']
 assert len(timeline)==130 and sum(x['duration_seconds'] for x in timeline)==SECONDS
 assert all(x['duration_seconds']==10 and x['start_seconds']==(x['slot']-1)*10 for x in timeline[:129])
 assert timeline[-1]['duration_seconds']==2 and timeline[-1]['start_seconds']==1290 and timeline[-1]['hold_final_frame']
 assert timeline[-1]['prompt']==timeline[-2]['prompt']
 assert sum(x['reuse'] for x in timeline)==30 and sum(x['reuse'] for x in timeline[:129])==29
 assert set(x['prompt'] for x in timeline)==set(range(1,101))
 for n in range(1,101):
  uses=[x for x in timeline if x['prompt']==n]
  assert sum(not x['reuse'] for x in uses)==1 and not uses[0]['reuse']
 edit=list(csv.DictReader((ROOT/'scene-voice-edit.csv').open(encoding='utf-8-sig')));assert len(edit)==130
 for c in ['en','vi']:
  rows=json.loads((ROOT/f'scripts/{c}.json').read_text())
  assert all(e['voice_'+c]==r['text'] for e,r in zip(edit[:129],rows)) and not edit[-1]['voice_'+c]
 files=list(sorted((ROOT/'prompts').glob('prompt-*.txt')));assert len(files)==10
 numbered=[]
 for p in files:
  parts=p.read_text(encoding='utf-8-sig').strip().split('\n\n');assert len(parts)==10
  for text in parts:
   numbered.append(int(re.match(r'(\d+)\.',text).group(1)))
   assert all(t in text for t in ['10-second','NO CHILDREN','NO AUDIO','NO SPEECH','KHÔNG CÓ HÌNH TRẺ EM','KHÔNG CÓ ÂM THANH, KHÔNG LỜI NÓI'])
 assert numbered==list(range(1,101))
 names=json.loads((ROOT/'tools/COUNTRY_FILE_NAMES.json').read_text());exports=ROOT/'downloads';exports.mkdir(exist_ok=True);delivery=[]
 for code,(label,stem) in names.items():
  rows=json.loads((ROOT/f'scripts/{code}.json').read_text());report=json.loads((ROOT/f'audio/{code}-report.json').read_text())
  assert len(rows)==CUES and [r['scene'] for r in rows]==list(range(1,130))
  assert all(r['duration_seconds']==10 and r['start_seconds']==(r['scene']-1)*10 for r in rows)
  assert report['status']=='created_pending_listening_review' and report['voice_id']==voices[code]['voice_id']
  expected=hashlib.sha256(json.dumps({'voice':report['voice_id'],'engine':report['engine'],'rows':rows},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
  assert report['config_hash']==expected,(code,'stale script')
  assert len(report['segments'])==CUES and report['closing_silence_seconds']==2
  for row,seg in zip(rows,report['segments']):
   assert row['scene']==seg['scene'] and row['text']==seg['text']
   assert not seg['word_truncation'] and seg['fitted_seconds']==10
   assert seg['tempo']<=1.3 and seg['speech_window_seconds']/seg['tempo']<=9.651,(code,row['scene'],'shorten localization')
  assert report['decoded_samples']==FRAMES and report['decoded_seconds']==SECONDS
  source=ROOT/'audio'/report['mp3'];master=ROOT/'audio'/report['flac']
  assert sha(source)==report['mp3_sha256'] and sha(master)==report['flac_sha256']
  process=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-i',str(source),'-f','s16le','-ar','24000','-ac','1','pipe:1'],stdout=subprocess.PIPE)
  size=0
  while block:=process.stdout.read(1024*1024):size+=len(block)
  assert process.wait()==0 and size==FRAMES*2,(code,'MP3 decoded duration')
  info=sf.info(master);assert (info.frames,info.samplerate,info.channels)==(FRAMES,24000,1)
  peak=0;count=0
  for i,b in enumerate(sf.blocks(master,blocksize=240000,dtype='float32')):
   assert np.isfinite(b).all();p=float(np.max(np.abs(b)));peak=max(peak,p)
   if i<CUES:assert p>.001,(code,i+1,'silent cue')
   else:assert i==CUES and len(b)==48000 and p<1e-6,(code,'closing silence')
   count+=1
  assert count==130 and peak<.999
  target=exports/f'{stem}-21m32s.mp3'
  if not target.exists():os.link(source,target)
  else:assert sha(target)==report['mp3_sha256']
  srt=(ROOT/f'scripts/{code}.srt').read_text(encoding='utf-8-sig')
  assert srt.count(' --> ')==129 and '00:21:20,000 --> 00:21:30,000' in srt
  delivery.append(dict(language=code,label=label,voice_id=report['voice_id'],gender=voices[code]['gender'],file='downloads/'+target.name,
   bytes=target.stat().st_size,sha256=report['mp3_sha256'],decoded_seconds=SECONDS,decoded_samples=FRAMES,sample_rate=24000,
   channels=1,narration_cues=CUES,non_silent_cues=CUES,closing_silence_seconds=2,max_tempo=max(s['tempo'] for s in report['segments'])))
  voices[code].update(audio_status='created_1292_seconds_pending_native_review',translation_status='prepared_and_technically_aligned',translation_method='assistant_prepared_separately_no_full_native_review')
  print('Verified',code,'21:32',flush=True)
 save(ROOT/'VOICE_PROFILES.json',profiles)
 manifest=dict(episode=85,topic='Angkor: The City and Its Water Network',seconds=SECONDS,voices=17,spoken_cues=CUES,
  closing_silence_seconds=2,generated_clip_seconds=10,timeline_slots=130,unique_prompts=100,reused_slots=30,reused_full_slots=29,
  closing_hold_seconds=2,prompt_txt_files=10,full_native_speaker_review=False,published=False,files=delivery)
 save(ROOT/'DELIVERY_MANIFEST.json',manifest)
 save(ROOT/'validation/final-delivery.json',dict(status='passed',decoded_samples_per_mp3=FRAMES,seconds_per_track=SECONDS,tracks=17,
  matched_scripts=17,non_silent_cues_per_track=CUES,closing_silence_seconds=2,prompt_guards_passed=100,prompt_txt_files=10,
  timeline_slots=130,reused_full_slots=29,closing_hold_seconds=2,limitations=['No full native-speaker review; localizations prepared separately by the assistant.','External factual sites blocked; see research notes.']))
 with zipfile.ZipFile(ROOT/'Angkor-085-production-kit.zip','w',zipfile.ZIP_DEFLATED) as z:
  for directory in ['scripts','prompts','research','titles-thumbnails','source-analysis','tools']:
   for p in sorted((ROOT/directory).rglob('*')):
    if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':z.write(p,str(p.relative_to(ROOT)))
  for name in ['KICH-BAN-CHINH.md','EDITING-GUIDE.md','BANG-TINH-130-DOAN.md','scene-voice-edit.csv','shot-reuse-map.json','VOICE_PROFILES.json','DELIVERY_MANIFEST.json','validation/final-delivery.json','validation/reference-access.json','validation/research-access.json']:
   z.write(ROOT/name,name)
 with zipfile.ZipFile(ROOT/'Angkor-085-17-voices-21m32s.zip','w',zipfile.ZIP_STORED) as z:
  for row in delivery:z.write(ROOT/row['file'],row['file'])
  z.write(ROOT/'DELIVERY_MANIFEST.json','DELIVERY_MANIFEST.json')
 for p in ROOT.glob('*.zip'):
  with zipfile.ZipFile(p) as z:assert z.testzip() is None
 state=json.loads((ROOT/'PRODUCTION_STATE.json').read_text());state.update(status='complete_pending_native_review',mp3_count=17)
 save(ROOT/'PRODUCTION_STATE.json',state)
 print('Delivery passed: 17 MP3, 100 prompts in 10 TXT, exact 21:32.',flush=True)

if __name__=='__main__':main()
