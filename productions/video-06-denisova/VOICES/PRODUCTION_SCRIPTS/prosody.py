"""Small, documented prosody controls around the user's unchanged TTS backend.

No SSML markup is inserted into narration. Voice IDs, reference voice and pitch
are preserved. Edge supplies word timings for gentle, bounded gain accents;
native Hmong uses phrase speed/level variation because it has no word timings.
"""
import array,json,math,re,threading,unicodedata,wave
from pathlib import Path
LOCAL=threading.local();STYLE_ID='science-documentary-expressive-v1'
EN_PACING_REPAIRS={52,57,61,64,68,83,109,110,111,119,122}
EN_INTENTS={**{i:'question' for i in [3,4,11,22,31,44,55,66,76,86,95,96,116]},**{i:'evidence' for i in [2,15,17,23,24,25,28,34,35,37,38,39,45,46,48,56,57,60,62,63,67,68,69,70,71,72,77,78,80,81,87,88,97,98,100,101,107,108,109,111]},**{i:'reflective' for i in [7,8,9,10,18,20,26,30,32,36,40,43,47,49,50,51,52,53,58,61,64,65,73,74,75,79,83,84,85,89,91,92,93,94,99,102,103,104,105,106,110,112,113,114,115,*range(117,127)]}}
KEYWORDS={
 'en-US':['related','relationship','ancestry','fragment','not','DNA','evidence','context','missing','Denisova','Denisovan','protein','genome'],
 'vi-VN':['ADN','caj','gene','không','quan hệ','tổ tiên','mẫu','bằng chứng'],
 'es-ES':['ADN','ancestría','ascendencia','relación','muestra','no','evidencia'],
 'fr-FR':['ADN','ascendance','relation','échantillon','pas','preuve'],
 'ja-JP':['DNA','祖先','関係','試料','証拠','ない'],
 'ko-KR':['DNA','조상','관계','표본','증거','않'],
 'de-DE':['DNA','Abstammung','Beziehung','Probe','nicht','Beweis'],
 'it-IT':['DNA','ascendenza','relazione','campione','non','prove'],
 'pt-PT':['ADN','ancestralidade','relação','amostra','não','evidência'],
 'nl-NL':['DNA','afkomst','verwant','relatie','monster','niet','bewijs'],
 'pl-PL':['DNA','pochodzenie','przodk','próbk','nie','dowod'],
 'sv-SE':['DNA','härkomst','släkt','prov','inte','bevis'],
 'da-DK':['DNA','herkomst','slægt','prøve','ikke','bevis'],
 'fi-FI':['DNA','suku','näyte','ei','todiste'],
 'nb-NO':['DNA','aner','slekts','prøve','ikke','bevis'],
 'cs-CZ':['DNA','původ','příbuz','vzorek','není','důkaz']}
def norm(s):return unicodedata.normalize('NFKC',s).casefold().strip('.,;:!?¿¡"“”()[] ')
def intent(locale,cue,text,part):
 if locale=='en-US':return EN_INTENTS.get(cue+1,'explain')
 if cue==11:return 'reflective'
 if any(x in text for x in ['?','？']):return 'question'
 if cue in [4,5,8,10]:return 'evidence'
 return 'explain'
def settings(locale,cue,text,part):
 name=intent(locale,cue,text,part)
 rate={'question':-2,'evidence':-3,'reflective':-4,'explain':1}[name]
 # Alternating short English sentences retain some local pacing after cue fit.
 if locale=='en-US' and part%2 and name!='reflective':rate+=2
 repair=locale=='en-US' and cue+1 in EN_PACING_REPAIRS
 if repair:rate=3  # Existing style range; preserve the immutable English wording.
 return dict(intent=name,rate=f'{rate:+d}%',pitch='+0Hz',volume='+0%',pause_seconds=.07 if repair else .16 if name=='question' else .12 if name=='reflective' else .07,trim_only_digital_zero_boundaries=repair)
def install_edge_adapter():
 import edge_tts
 if getattr(edge_tts.Communicate,'_science_prosody',False):return
 original=edge_tts.Communicate
 class Communicate(original):
  _science_prosody=True
  def __init__(self,text,voice,**kwargs):
   cfg=getattr(LOCAL,'config',{})
   kwargs.update(rate=cfg.get('rate','+0%'),pitch='+0Hz',volume='+0%',boundary='WordBoundary')
   super().__init__(text,voice,**kwargs)
   self._metadata_path=getattr(LOCAL,'metadata_path',None)
  async def save(self,audio_fname,metadata_fname=None):
   return await super().save(audio_fname,self._metadata_path or metadata_fname)
 edge_tts.Communicate=Communicate
def begin(locale,cue,text,path,part):
 LOCAL.config=settings(locale,cue,text,part);LOCAL.metadata_path=str(path.with_suffix('.words.jsonl'))
 return LOCAL.config
def style_wav(path,locale,cfg):
 metadata=path.with_suffix('.words.jsonl');events=[]
 if metadata.exists():
  for line in metadata.read_text().splitlines():
   e=json.loads(line)
   if e.get('type')=='WordBoundary':events.append(e)
 with wave.open(str(path),'rb') as f:
  assert f.getnchannels()==1 and f.getsampwidth()==2
  rate=f.getframerate();samples=array.array('h');samples.frombytes(f.readframes(f.getnframes()))
 chosen=[];keys=[norm(x) for x in KEYWORDS.get(locale,[])]
 for e in events:
  word=norm(e.get('text',''))
  if not word or not any(word==k or (len(k)>3 and (word.startswith(k) or (locale in ['ja-JP','ko-KR'] and k in word))) for k in keys):continue
  a=max(0,int(e['offset']/1e7*rate));b=min(len(samples),int((e['offset']+e['duration'])/1e7*rate))
  if b<=a:continue
  if chosen and a-chosen[-1]['end_frame']<rate*.6:continue
  chosen.append(dict(word=e['text'],start_frame=a,end_frame=b))
  if len(chosen)>=2:break
 # A gentle1.2dB accent, with30ms ramps. It changes level, not pitch/timbre.
 gain=10**(1.2/20);ramp=max(1,int(rate*.03))
 peak=max((abs(x) for x in samples),default=0)
 if chosen and peak*gain>32112:samples=array.array('h',(round(x*32112/(peak*gain)) for x in samples))
 for e in chosen:
  a,b=e['start_frame'],e['end_frame']
  for j in range(a,b):
   w=min(1,(j-a)/ramp,(b-1-j)/ramp);samples[j]=max(-32760,min(32760,round(samples[j]*(1+(gain-1)*max(0,w)))))
 peak=max((abs(x) for x in samples),default=0)
 if peak>32112:samples=array.array('h',(round(x*32112/peak) for x in samples))
 removed_leading=removed_trailing=0
 if cfg.get('trim_only_digital_zero_boundaries'):
  guard=round(rate*.03);a=0;b=len(samples)
  while a<b and samples[a]==0:a+=1
  while b>a and samples[b-1]==0:b-=1
  removed_leading=max(0,a-guard);removed_trailing=max(0,len(samples)-b-guard)
  if removed_leading or removed_trailing:
   samples=samples[removed_leading:len(samples)-removed_trailing if removed_trailing else len(samples)]
   for accent in chosen:
    accent['start_frame']-=removed_leading;accent['end_frame']-=removed_leading
 samples.extend(array.array('h',[0])*round(rate*cfg['pause_seconds']))
 tmp=path.with_suffix('.styled.wav')
 with wave.open(str(tmp),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(samples.tobytes())
 tmp.replace(path)
 note=dict(style_id=STYLE_ID,locale=locale,settings=cfg,word_boundary_count=len(events),word_accents=chosen,pitch_shift_applied=False,removed_leading_digital_zero_frames=removed_leading,removed_trailing_digital_zero_frames=removed_trailing,digital_silence_guard_seconds=.03)
 path.with_suffix('.style.json').write_text(json.dumps(note,ensure_ascii=False))
 return note
