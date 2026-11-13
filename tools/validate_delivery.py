import csv,hashlib,json,os,re,subprocess,zipfile
from pathlib import Path
import numpy as np
import soundfile as sf
ROOT=Path(__file__).resolve().parents[1]
SECONDS=1320
FRAMES=31680000

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()

def save(path,data):Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

def names():
 return json.loads((ROOT/'tools/COUNTRY_FILE_NAMES.json').read_text())

def main():
 profiles=json.loads((ROOT/'VOICE_PROFILES.json').read_text());voices={x['language']:x for x in profiles['profiles']}
 assert len(voices)==17 and sum(x['gender']=='Male' for x in voices.values())==16
 assert voices['en']['voice_id']=='en-US-AndrewNeural' and voices['vi']['voice_id']=='vi-VN-NamMinhNeural'
 assert voices['hmn']['voice_id']=='hmong-female-3' and voices['hmn']['gender']=='Female'
 plan=json.loads((ROOT/'shot-reuse-map.json').read_text());timeline=plan['timeline']
 assert len(timeline)==132 and sum(x['duration_seconds'] for x in timeline)==1320
 assert sum(x['reuse'] for x in timeline)==72
 assert set(x['prompt'] for x in timeline)==set(range(1,61))
 assert all(x['start_seconds']==(x['slot']-1)*10 for x in timeline)
 assert timeline[-1]['start_seconds']+10==1320
 edit=list(csv.DictReader((ROOT/'scene-voice-edit.csv').open(encoding='utf-8-sig')))
 assert len(edit)==132
 for code in ['en','vi']:
  rows=json.loads((ROOT/f'scripts/{code}.json').read_text())
  assert all(e['voice_'+code]==r['text'] for e,r in zip(edit,rows))
 for p in range(1,61):
  uses=[x for x in timeline if x['prompt']==p]
  assert sum(not x['reuse'] for x in uses)==1 and not uses[0]['reuse']
 numbered=[]
 for file in sorted((ROOT/'prompts').glob('prompt-*.txt')):
  parts=file.read_text(encoding='utf-8-sig').strip().split('\n\n');assert len(parts)==10
  for part in parts:
   numbered.append(int(re.match(r'(\d+)\.',part).group(1)))
   assert all(t in part for t in ['10-second','NO CHILDREN','NO AUDIO','NO SPEECH','KHÔNG CÓ HÌNH TRẺ EM','KHÔNG CÓ ÂM THANH, KHÔNG LỜI NÓI'])
 assert numbered==list(range(1,61))
 exports=ROOT/'downloads';exports.mkdir(exist_ok=True);files=[]
 for code,(label,stem) in names().items():
  rows=json.loads((ROOT/f'scripts/{code}.json').read_text());report=json.loads((ROOT/f'audio/{code}-report.json').read_text())
  assert len(rows)==132 and [x['scene'] for x in rows]==list(range(1,133))
  assert all(x['duration_seconds']==10 and x['start_seconds']==(x['scene']-1)*10 for x in rows)
  assert report['status']=='created_pending_listening_review',(code,report['status'])
  assert report['voice_id']==voices[code]['voice_id']
  expected=hashlib.sha256(json.dumps({'voice':report['voice_id'],'engine':report['engine'],'rows':rows},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
  assert report['config_hash']==expected,(code,'stale script hash')
  assert len(report['segments'])==132
  for row,seg in zip(rows,report['segments']):
   assert row['scene']==seg['scene'] and row['text']==seg['text']
   assert not seg['word_truncation'] and seg['fitted_seconds']==10
   assert seg['tempo']<=1.3,(code,row['scene'],'needs shorter localization')
   assert seg['speech_window_seconds']/seg['tempo']<=9.651
  assert report['decoded_samples']==FRAMES and report['decoded_seconds']==SECONDS
  source=ROOT/'audio'/report['mp3'];master=ROOT/'audio'/report['flac']
  assert sha(source)==report['mp3_sha256'] and sha(master)==report['flac_sha256']
  decoded=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-i',str(source),'-f','s16le','-ar','24000','-ac','1','pipe:1'],stdout=subprocess.PIPE)
  decoded_bytes=0
  while block:=decoded.stdout.read(1024*1024):decoded_bytes+=len(block)
  assert decoded.wait()==0 and decoded_bytes==FRAMES*2,(code,'MP3 decoded duration')
  info=sf.info(master);assert (info.frames,info.samplerate,info.channels)==(FRAMES,24000,1)
  peak=0;count=0
  for b in sf.blocks(master,blocksize=240000,dtype='float32'):
   assert np.isfinite(b).all() and float(np.max(np.abs(b)))>.001
   peak=max(peak,float(np.max(np.abs(b))));count+=1
  assert count==132 and peak<.999
  path=exports/f'{stem}-22m00s.mp3'
  if not path.exists():os.link(source,path)
  else:assert sha(path)==report['mp3_sha256']
  srt=(ROOT/f'scripts/{code}.srt').read_text(encoding='utf-8-sig')
  assert srt.count(' --> ')==132 and '00:21:50,000 --> 00:22:00,000' in srt
  files.append({'language':code,'label':label,'voice_id':report['voice_id'],'gender':voices[code]['gender'],
                'file':'downloads/'+path.name,'bytes':path.stat().st_size,'sha256':report['mp3_sha256'],
                'decoded_seconds':1320,'decoded_samples':FRAMES,'sample_rate':24000,'channels':1,
                'narration_cues':132,'non_silent_cues':132,'max_tempo':max(x['tempo'] for x in report['segments'])})
  voices[code].update(audio_status='created_1320_seconds_pending_native_review',translation_status='prepared_and_technically_aligned')
  voices[code]['translation_method']='assistant_prepared_separately_no_full_native_review'
  print('Verified',code,'22:00',flush=True)
 save(ROOT/'VOICE_PROFILES.json',profiles)
 manifest={'episode':40,'topic':'Flores: Caves, Volcanoes, and an Unexpected Past','seconds':1320,'voices':17,
           'generated_clip_seconds':10,'timeline_slots':132,'unique_prompts':60,'reused_slots':72,'prompt_txt_files':6,
           'full_native_speaker_review':False,'published':False,'files':files}
 save(ROOT/'DELIVERY_MANIFEST.json',manifest)
 save(ROOT/'validation/final-delivery.json',{'status':'passed','decoded_samples_per_mp3':FRAMES,'seconds_per_track':1320,
      'tracks':17,'matched_scripts':17,'non_silent_cues_per_track':132,'prompt_guards_passed':60,'timeline_slots':132,'reuse_slots':72,
      'limitations':['No full native-speaker review; localizations were prepared separately by the assistant.','External factual pages blocked; see research notes.']})
 with zipfile.ZipFile(ROOT/'Flores-040-production-kit.zip','w',zipfile.ZIP_DEFLATED) as z:
  for directory in ['scripts','prompts','research','titles-thumbnails','source-analysis','tools']:
   for p in sorted((ROOT/directory).rglob('*')):
    if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith(('.pyc','.review.txt')):z.write(p,str(p.relative_to(ROOT)))
  for name in ['KICH-BAN-CHINH.md','EDITING-GUIDE.md','BANG-TINH-132-DOAN.md','scene-voice-edit.csv','shot-reuse-map.json','VOICE_PROFILES.json','DELIVERY_MANIFEST.json','validation/final-delivery.json','validation/reference-access.json','validation/research-access.json']:
   z.write(ROOT/name,name)
 with zipfile.ZipFile(ROOT/'Flores-040-17-voices-22m00s.zip','w',zipfile.ZIP_STORED) as z:
  for row in files:z.write(ROOT/row['file'],row['file'])
  z.write(ROOT/'DELIVERY_MANIFEST.json','DELIVERY_MANIFEST.json')
 for p in ROOT.glob('*.zip'):
  with zipfile.ZipFile(p) as z:assert z.testzip() is None
 state=json.loads((ROOT/'PRODUCTION_STATE.json').read_text());state.update(status='complete_pending_native_review',mp3_count=17)
 save(ROOT/'PRODUCTION_STATE.json',state)
 print('Delivery validation passed: 17 MP3, 60 prompts, 132 slots, exact 22:00',flush=True)

if __name__=='__main__':main()
