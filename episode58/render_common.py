import array,asyncio,concurrent.futures,difflib,hashlib,html,json,os,re,subprocess,sys,threading,time,unicodedata,wave
from pathlib import Path
R=Path(__file__).parent;TARGET=1362;FRAMES=65376000;PREFIX='BONE_TRACES_58';S=R/'voice/scripts';A=R/'voice/audio';A.mkdir(parents=True,exist_ok=True)
PROFILES={p['locale']:p for p in json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text())['profiles']}
SLUG={'en-US':'My_Tieng_Anh','vi-VN':'Viet_Nam_Adam','es-ES':'Tay_Ban_Nha','fr-FR':'Phap','ja-JP':'Nhat_Ban','ko-KR':'Han_Quoc','de-DE':'Duc','it-IT':'Y','pt-PT':'Bo_Dao_Nha','nl-NL':'Ha_Lan','pl-PL':'Ba_Lan','sv-SE':'Thuy_Dien','da-DK':'Dan_Mach','fi-FI':'Phan_Lan','nb-NO':'Na_Uy','cs-CZ':'Sec','mww':'Hmong_Trang_Nu'}
KEYWORDS={'en-US': ['food', 'water', 'smoke', 'cold', 'bone', 'evidence', 'tomorrow', 'storage'], 'es-ES': ['alimento', 'agua', 'humo', 'frío', 'hueso', 'prueba'], 'fr-FR': ['nourriture', 'eau', 'fumée', 'froid', 'os', 'preuve'], 'ja-JP': ['食', '水', '煙', '骨', '証拠'], 'ko-KR': ['음식', '물', '연기', '뼈', '증거'], 'de-DE': ['Nahrung', 'Wasser', 'Rauch', 'Kälte', 'Knochen', 'Beleg'], 'it-IT': ['cibo', 'acqua', 'fumo', 'freddo', 'ossa', 'prove'], 'pt-PT': ['alimento', 'água', 'fumo', 'frio', 'osso', 'prova'], 'nl-NL': ['voedsel', 'water', 'rook', 'kou', 'bot', 'bewijs'], 'pl-PL': ['żywność', 'woda', 'dym', 'kości', 'dowód'], 'sv-SE': ['mat', 'vatten', 'rök', 'kyla', 'ben', 'bevis'], 'da-DK': ['mad', 'vand', 'røg', 'kulde', 'knogler', 'bevis'], 'fi-FI': ['ruoka', 'vesi', 'savu', 'kylmä', 'luu', 'todiste'], 'nb-NO': ['mat', 'vann', 'røyk', 'kulde', 'bein', 'bevis'], 'cs-CZ': ['jídlo', 'voda', 'kouř', 'chlad', 'kosti', 'důkaz']}
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
  if not .55<=tempo<=1.65:raise RuntimeError(f'Pacing needs repair: {locale},cue{i+1},tempo{tempo:.4f}; completed speech checkpoints retained')
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
 data={'status':'passed','locale':locale,'voice_id':profile['voice_id'],'gender':profile['gender'],'engine':profile['engine'],'source_commit':profile['source_commit'],'target_seconds':target,'decoded_frames_48000':n,'decoded_seconds':n/48000,'filename':dst.name,'bytes':dst.stat().st_size,'sha256':digest(dst),'script_sha256':digest(S/f'{locale}.json'),'cues':report,'pitch_shift_applied':False,'voice_identity_preserved':True,'narration_style_id':'science-documentary-expressive-v1','prosody_method':'Native phrase rate and question/reflective pacing plus at most two1.2dB word accents per request' if locale not in ['mww','vi-VN'] else 'Native punctuation and small phrase pauses, pitch-preserving final chapter fit; no pitch shift','word_metadata_pieces':len(rawmeta),'minimum_word_coverage_ratio':min([x['coverage'] for x in rawmeta]) if rawmeta else None,'word_accents':sum(x['accents'] for x in rawmeta),'independent_native_listening_review':False,'timing_alignment':str(len(rows))+'Englishcues' if locale=='en-US' else '13 shared chapter boundaries'}
 if locale=='mww':data.update(reference_sha256=profile['reference_sha256'],white_hmong_dialect_independently_verified=False)
 if locale=='vi-VN':data.update(sdk_version='3.8.3',preset_sha256=profile['preset_sha256'],model_revision=profile['model_revision'],native_backend='Melo1.3.1worker/VieNeuONNXFP32')
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
