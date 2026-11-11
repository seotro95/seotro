import array,asyncio,concurrent.futures,difflib,hashlib,html,json,os,re,subprocess,sys,threading,time,unicodedata,wave
from pathlib import Path
R=Path(__file__).parent;TARGET=1352;FRAMES=64896000;PREFIX='LAND_BRIDGES_38';S=R/'voice/scripts';A=R/'voice/audio';A.mkdir(parents=True,exist_ok=True)
PROFILES={p['locale']:p for p in json.loads((R/'BASELINE_VOICE_PROFILES.json').read_text())['profiles']}
SLUG={'en-US':'My_Tieng_Anh','vi-VN':'Viet_Nam','es-ES':'Tay_Ban_Nha','fr-FR':'Phap','ja-JP':'Nhat_Ban','ko-KR':'Han_Quoc','de-DE':'Duc','it-IT':'Y','pt-PT':'Bo_Dao_Nha','nl-NL':'Ha_Lan','pl-PL':'Ba_Lan','sv-SE':'Thuy_Dien','da-DK':'Dan_Mach','fi-FI':'Phan_Lan','nb-NO':'Na_Uy','cs-CZ':'Sec','mww':'Hmong_Trang_Nu'}
KEYWORDS={'en-US':['water','ice','land','sea','evidence','Beringia','Doggerland','Sunda','Sahul','channel'],'vi-VN':['biển','băng','đất','bằng','Beringia','Sahul'],'es-ES':['mar','hielo','tierra','prueba'],'fr-FR':['mer','glace','terre','preuve'],'ja-JP':['海','氷','陸','証拠'],'ko-KR':['바다','빙하','육지','증거'],'de-DE':['Meer','Eis','Land','Beleg'],'it-IT':['mare','ghiaccio','terra','prove'],'pt-PT':['mar','gelo','terra','prova'],'nl-NL':['zee','ijs','land','bewijs'],'pl-PL':['morze','lód','ląd','dowod'],'sv-SE':['hav','is','land','bevis'],'da-DK':['hav','is','land','bevis'],'fi-FI':['meri','jää','maa','todiste'],'nb-NO':['hav','is','land','bevis'],'cs-CZ':['moře','led','pevnina','důkaz']}
LOCAL=threading.local()
def run(args):subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-threads','1',*map(str,args)],check=True)
def seconds(p):
 with wave.open(str(p)) as w:return w.getnframes()/w.getframerate()
def digest(p):return hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
def normalized(s):return ''.join(c for c in unicodedata.normalize('NFKC',html.unescape(s)).casefold() if c.isalnum())
def split(text,limit=700):
 # Sentence boundaries require whitespace after Latin punctuation; never split decimal or grouped numeric values.
 sentences=re.split(r'(?<=[.!?])\s+|(?<=[。！？])',text.strip());out=[];current=''
 for sentence in sentences:
  sentence=sentence.strip()
  if not sentence:continue
  if len(sentence)>limit:
   if current:out.append(current);current=''
   words=sentence.split();piece=''
   if len(words)<2:out.extend(sentence[i:i+limit] for i in range(0,len(sentence),limit));continue
   for word in words:
    if piece and len(piece+' '+word)>limit:out.append(piece);piece=''
    piece=(piece+' '+word).strip()
   if piece:out.append(piece)
  elif current and len(current+' '+sentence)>limit:out.append(current);current=sentence
  else:current=(current+' '+sentence).strip()
 if current:out.append(current)
 assert out and all(len(x)<=1200 for x in out)
 return out
def finish(locale,rows,raws,out=None,target=TARGET):
 out=out or A/locale;report=[];prepared=[]
 for i,(row,paths) in enumerate(zip(rows,raws)):
  concat=out/'join.txt';concat.write_text(''.join("file '"+str(p.resolve())+"'\n" for p in paths));joined=out/f'joined-{i:03}.wav'
  run(['-f','concat','-safe','0','-i',concat,'-ar','48000','-ac','1','-c:a','pcm_s16le',joined])
  raw=seconds(joined);duration=row['end']-row['start'];pause=.16 if duration>2 else .08;tempo=raw/(duration-pause)
  if not .45<=tempo<=1.65:raise RuntimeError(f'Pacing needs repair: {locale},cue{i+1},tempo{tempo:.4f}; completed speech checkpoints retained')
  dest=out/f'cue-{i:03}.wav';frames=round(duration*48000)
  run(['-i',joined,'-af',f'atempo={tempo:.10f},apad,atrim=end_sample={frames}','-ar','48000','-ac','1','-c:a','pcm_s16le',dest])
  with wave.open(str(dest)) as w:assert w.getnframes()==frames
  report.append({'id':row['id'],'start':row['start'],'end':row['end'],'raw_seconds':raw,'tempo':tempo,'trailing_pause_target':pause,'parts':len(paths)})
  prepared.append(dest);joined.unlink()
 concat=out/'final.txt';concat.write_text(''.join("file '"+str(p.resolve())+"'\n" for p in prepared))
 dst=out/(f'{PREFIX}_{SLUG[locale]}.mp3' if target==TARGET else f'{PREFIX}_EN_PREVIEW_30s.mp3')
 run(['-f','concat','-safe','0','-i',concat,'-af','loudnorm=I=-19:TP=-2:LRA=8','-ar','48000','-ac','1','-c:a','libmp3lame','-b:a','96k',dst])
 decoded=out/'decoded.wav';run(['-i',dst,'-ar','48000','-ac','1','-c:a','pcm_s16le',decoded])
 with wave.open(str(decoded)) as w:n=w.getnframes();assert n==target*48000,(locale,n,target)
 decoded.unlink();profile=PROFILES[locale];rawmeta=[json.loads(p.read_text()) for p in out.glob('raw-*.meta.json')]
 data={'status':'passed','locale':locale,'voice_id':profile['voice_id'],'gender':profile['gender'],'engine':profile['engine'],'source_commit':profile['source_commit'],'target_seconds':target,'decoded_frames_48000':n,'decoded_seconds':n/48000,'filename':dst.name,'bytes':dst.stat().st_size,'sha256':digest(dst),'script_sha256':digest(S/f'{locale}.json'),'cues':report,'pitch_shift_applied':False,'voice_identity_preserved':True,'narration_style_id':'science-documentary-expressive-v1','prosody_method':'Native phrase rate and question/reflective pacing plus at most two1.2dB word accents per request' if locale!='mww' else 'Native phrase speed0.98–1.02, small inter-phrase pauses, clear-v1 reference timbre','word_metadata_pieces':len(rawmeta),'minimum_word_coverage_ratio':min([x['coverage'] for x in rawmeta]) if rawmeta else None,'word_accents':sum(x['accents'] for x in rawmeta),'independent_native_listening_review':False,'timing_alignment':str(len(rows))+'Englishcues' if locale=='en-US' else '14sharedchapterboundaries'}
 if locale=='mww':data.update(reference_sha256=profile['reference_sha256'],white_hmong_dialect_independently_verified=False)
 (out/'render_report.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
 for p in prepared:p.unlink()
 print(json.dumps({'VOICE_DONE':locale,'seconds':target,'frames':n,'min_tempo':min(x['tempo'] for x in report),'max_tempo':max(x['tempo'] for x in report),'word_accents':data['word_accents']}),flush=True)
 return data
def accent(path,words,locale):
 with wave.open(str(path)) as w:
  assert w.getnchannels()==1 and w.getsampwidth()==2;rate=w.getframerate();samples=array.array('h');samples.frombytes(w.readframes(w.getnframes()))
 keys=[normalized(x) for x in KEYWORDS.get(locale,[])];selected=[]
 for e in words:
  word=normalized(e.get('text',''))
  if not any(word==k or (len(k)>2 and word.startswith(k)) or (locale in ['ja-JP','ko-KR'] and k in word) for k in keys):continue
  a=max(0,round(e['offset']/1e7*rate));b=min(len(samples),round((e['offset']+e['duration'])/1e7*rate))
  if b<=a or (selected and a-selected[-1][1]<rate*.65):continue
  selected.append((a,b))
  if len(selected)==2:break
 gain=10**(1.2/20);peak=max(map(abs,samples),default=0)
 if selected and peak*gain>32112:samples=array.array('h',(round(x*32112/(peak*gain)) for x in samples))
 ramp=max(1,round(rate*.03))
 for a,b in selected:
  for j in range(a,b):
   weight=max(0,min(1,(j-a)/ramp,(b-1-j)/ramp));samples[j]=round(samples[j]*(1+(gain-1)*weight))
 with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(samples.tobytes())
 return len(selected)
def online(locale,preview=False):
 assert json.loads((R/'DOCUMENT_DELIVERY_STATE.json').read_text())['documents_published']
 if locale!='en-US':assert (S/f'{locale}.reviewed38').exists(),'Localized context review marker missing'
 import edge_tts,edge_tts.communicate,edge_tts.voices
 for mod in [edge_tts.communicate,edge_tts.voices]:
  if os.environ.get('SSL_CERT_FILE'):mod._SSL_CTX.load_verify_locations(cafile=os.environ['SSL_CERT_FILE'])
 sys.path.insert(0,str(R.parent/'melo'));import online_backend
 catalog=online_backend.get_catalog();profile=PROFILES[locale];chosen=[v for v in catalog if v['ShortName']==profile['voice_id']]
 assert len(chosen)==1 and chosen[0]['Gender']=='Male' and chosen[0]['Locale']==locale
 rows=json.loads((S/f'{locale}.json').read_text());out=R/'voice/preview' if preview else A/locale;out.mkdir(parents=True,exist_ok=True);target=30 if preview else TARGET
 if preview:rows=rows[:3]
 old=out/'render_report.json'
 if old.exists():
  data=json.loads(old.read_text())
  if data['target_seconds']==target and data['script_sha256']==digest(S/f'{locale}.json') and data['sha256']==digest(out/data['filename']):return data
 async def download(text,voice,output):
  err=None
  for attempt in range(5):
   try:
    async def receive():
     words=[];stream=edge_tts.Communicate(text,voice,rate=LOCAL.rate,volume='+0%',pitch='+0Hz',boundary='WordBoundary',proxy=os.environ.get('HTTPS_PROXY'),connect_timeout=20,receive_timeout=60)
     with Path(output).open('wb') as f:
      async for chunk in stream.stream():
       if chunk['type']=='audio':f.write(chunk['data'])
       elif chunk['type']=='WordBoundary':words.append(chunk)
     assert Path(output).stat().st_size>0
     Path(output).with_suffix('.words.json').write_text(json.dumps(words,ensure_ascii=False))
    await asyncio.wait_for(receive(),timeout=150);return
   except Exception as e:
    err=e
    if getattr(e,'status',None) in [401,403,429]:raise
    print('TTS_TRANSIENT',locale,type(e).__name__,'attempt',attempt+1,'of5',flush=True)
    if attempt<4:await asyncio.sleep([5,15,30,60][attempt])
  raise err
 online_backend.download_audio=download;records=[];raws=[]
 for i,row in enumerate(rows):
  texts=split(row['voice'],limit=700);paths=[]
  for j,text in enumerate(texts):
   path=out/f'raw-{i+1:03}-{j+1:02}.wav';paths.append(path);records.append((i,j,text,path))
  raws.append(paths)
 def synth(item):
  i,j,text,path=item;rate=-8 if locale=='en-US' else -1
  if '?' in text or '？' in text:rate-=1
  if i>=len(rows)-max(1,len(rows)//12):rate-=2
  if j%2:rate+=1
  LOCAL.rate=f'{rate:+d}%';signature=hashlib.sha256((text+'\0'+profile['voice_id']+'\0'+LOCAL.rate).encode()).hexdigest();meta=path.with_suffix('.meta.json')
  if path.exists() and meta.exists() and json.loads(meta.read_text()).get('request_signature')==signature:return path
  for attempt in range(3):
   path.unlink(missing_ok=True);online_backend.handle({'op':'render','language':locale,'voice':profile['voice_id'],'text':text,'output':str(path)})
   words=json.loads(path.with_suffix('.edge.words.json').read_text());actual=''.join(w['text'] for w in words)
   coverage=difflib.SequenceMatcher(None,normalized(text),normalized(actual),autojunk=False).ratio()
   if coverage>=.97:break
   print('RETRY_INCOMPLETE',locale,i+1,j+1,coverage,flush=True)
   if attempt==2:raise RuntimeError(f'Incomplete spoken text:{locale}/{i+1}/{j+1}')
  accents=accent(path,words,locale);meta.write_text(json.dumps({'request_signature':signature,'coverage':coverage,'voice_id':profile['voice_id'],'rate':LOCAL.rate,'accents':accents,'source_words':len(words)}))
  time.sleep(.25);return path
 pending=[];completed=0
 with concurrent.futures.ThreadPoolExecutor(max_workers=1 if locale in ['en-US','vi-VN'] else 2) as pool:
  futures={pool.submit(synth,item):item for item in records}
  for future in concurrent.futures.as_completed(futures):
   item=futures[future]
   try:future.result();completed+=1
   except edge_tts.exceptions.NoAudioReceived:
    pending.append({'cue_index':item[0],'part_index':item[1],'filename':item[3].name,'reason':'NoAudioReceived after five bounded attempts'})
    print('TTS_PENDING',locale,item[0]+1,item[1]+1,flush=True)
   except Exception:
    for other in futures:other.cancel()
    raise
   if completed and completed%10==0:print('SYNTH',locale,completed,len(records),flush=True)
 if pending:
  (out/'pending_speech.json').write_text(json.dumps(pending,indent=2))
  raise RuntimeError(f'{locale}: {len(pending)}parts remain unavailable; all successful speech retained; retry only pending parts later')
 (out/'pending_speech.json').unlink(missing_ok=True)
 return finish(locale,rows,raws,out=out,target=target)
if __name__=='__main__':online(sys.argv[1],preview='--preview' in sys.argv)
