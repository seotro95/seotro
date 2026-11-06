"""Local CPU translation on the GitHub runner; no external language-model API."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,tarfile,time,urllib.request

ROOT=Path(__file__).resolve().parent
TARGETS={'vi':('Vietnamese','bạn / chúng ta'),'es':('Spanish as spoken in Spain','tú'),'fr':('French as spoken in France','vous'),'ja':('Japanese','polite documentary style, です・ます'),'ko':('Korean','polite documentary style, 합니다'),'de':('German','ihr'),'it':('Italian','voi'),'pt':('European Portuguese','vocês'),'nl':('Dutch as spoken in the Netherlands','je'),'pl':('Polish','wy'),'sv':('Swedish','du'),'da':('Danish','du'),'fi':('Finnish','natural neutral documentary address'),'no':('Norwegian Bokmål','du'),'cs':('Czech','vy'),'hi':('Hindi','आप')}
GLOSSARY={
 'vi':'basin = bồn địa; boulder = tảng đá lớn; friction = ma sát; permafrost = tầng đất đóng băng vĩnh cửu; thaw slump = vùng sụt lở do đất tan băng; timber = gỗ xây dựng; annual tree rings = vòng sinh trưởng hằng năm của cây; mire = đầm lầy than bùn; radiocarbon = cacbon phóng xạ; evidence = bằng chứng; hypothesis = giả thuyết. Use natural Vietnamese, not foreign calques.',
 'es':'basin = la cuenca geográfica; timber = la madera de construcción; boulder = un bloque rocoso; friction = la fricción; thaw slump = un deslizamiento por deshielo; permafrost = el suelo permanentemente helado; annual tree rings = los anillos de crecimiento anual; mire = la turbera. Check noun genders: LA cuenca, LA madera, EL bloque, EL suelo.',
 'fr':'basin = bassin géographique; boulder = bloc rocheux; friction = frottement; permafrost = pergélisol; thaw slump = glissement de terrain lié au dégel; timber = bois de construction; tree rings = cernes annuels; mire = tourbière.',
 'de':'basin = Becken; boulder = Felsblock; friction = Reibung; permafrost = Dauerfrostboden; thaw slump = Auftaurutschung; timber = Bauholz; annual tree rings = Jahresringe; mire = Moor.',
 'ja':'basin = 盆地; boulder = 岩塊; friction = 摩擦; permafrost = 永久凍土; thaw slump = 凍土の融解による地滑り; timber = 建築用木材; annual tree rings = 年輪; mire = 泥炭地; hypothesis = 仮説; evidence = 証拠.',
 'ko':'basin = 분지; boulder = 바위 덩어리; friction = 마찰; permafrost = 영구동토층; thaw slump = 해빙에 따른 사면 붕괴; timber = 건축용 목재; tree rings = 나이테; mire = 이탄 습지; hypothesis = 가설; evidence = 증거.',
 'it':'basin = bacino geografico; boulder = masso roccioso; friction = attrito; permafrost = terreno permanentemente gelato; thaw slump = frana da disgelo; timber = legname da costruzione; tree rings = anelli di accrescimento; mire = torbiera.',
 'pt':'basin = bacia geográfica; boulder = bloco rochoso; friction = atrito; permafrost = solo permanentemente congelado; thaw slump = deslizamento por degelo; timber = madeira de construção; tree rings = anéis de crescimento; mire = turfeira.',
 'nl':'basin = geografisch bekken; boulder = rotsblok; friction = wrijving; permafrost = permanent bevroren bodem; thaw slump = afschuiving door dooi; timber = bouwhout; tree rings = jaarringen; mire = veengebied.',
 'pl':'basin = kotlina; boulder = blok skalny; friction = tarcie; permafrost = wieczna zmarzlina; thaw slump = osuwisko związane z rozmarzaniem; timber = drewno budowlane; tree rings = słoje przyrostu rocznego; mire = torfowisko.',
 'sv':'basin = geografisk sänka; boulder = stenblock; friction = friktion; permafrost = permafrost; thaw slump = ras orsakat av upptining; timber = byggnadsvirke; tree rings = årsringar; mire = torvmark.',
 'da':'basin = geografisk lavning; boulder = stenblok; friction = friktion; permafrost = permafrost; thaw slump = skred forårsaget af optøning; timber = bygningstømmer; tree rings = årringe; mire = tørvemose.',
 'fi':'basin = maaston allas; boulder = lohkare; friction = kitka; permafrost = ikirouta; thaw slump = sulamisvyöry; timber = rakennuspuu; tree rings = vuosirenkaat; mire = turvesuo.',
 'no':'basin = senkning i terrenget; boulder = steinblokk; friction = friksjon; permafrost = permafrost; thaw slump = utglidning ved tining; timber = bygningstømmer; tree rings = årringer; mire = torvmyr.',
 'cs':'basin = pánev; boulder = skalní balvan; friction = tření; permafrost = trvale zmrzlá půda; thaw slump = sesuv v důsledku rozmrzání; timber = stavební dřevo; tree rings = letokruhy; mire = rašeliniště.',
 'hi':'basin = भू-आकृतिक द्रोणी; boulder = विशाल शिलाखंड; friction = घर्षण; permafrost = स्थायी रूप से जमी भूमि; thaw slump = जमी भूमि के पिघलने से होने वाला भूस्खलन; timber = निर्माण की लकड़ी; annual tree rings = वृक्ष के वार्षिक वलय; mire = पीट दलदल; hypothesis = परिकल्पना; evidence = साक्ष्य.'}
def download(url,path,sha):
 if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==sha:return
 h=hashlib.sha256()
 with urllib.request.urlopen(url,timeout=180) as src,path.open('wb') as dst:
  while data:=src.read(1024*1024):dst.write(data);h.update(data)
 if h.hexdigest()!=sha:raise ValueError('Download checksum mismatch: '+path.name)

def prepare():
 cache=Path(os.environ.get('RUNNER_TEMP',str(ROOT)))/'translation-llm';cache.mkdir(exist_ok=True)
 archive=cache/'llama.tar.gz'
 download('https://github.com/ggml-org/llama.cpp/releases/download/b10199/llama-b10199-bin-ubuntu-x64.tar.gz',archive,'16d63bfb5c7e1c1656d940de398456ed2972af16ab5a0961f88c5929bc4fe58a')
 with tarfile.open(archive,'r:gz') as tar:tar.extractall(cache/'bin',filter='data')
 binary=next((cache/'bin').rglob('llama-server'));binary.chmod(0o755)
 model=cache/'Qwen3-4B-Instruct-2507-Q4_K_M.gguf'
 download('https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/resolve/6823cbe023756796ec86dc37864be826bfcd9fde/Qwen3-4B-Instruct-2507-Q4_K_M.gguf',model,'3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597')
 log=(cache/'server.log').open('w')
 process=subprocess.Popen([str(binary),'-m',str(model),'--host','127.0.0.1','--port','8941','-t','4','-c','8192','--parallel','1','--jinja'],stdout=log,stderr=log)
 for _ in range(240):
  if process.poll() is not None:raise RuntimeError((cache/'server.log').read_text()[-2500:])
  try:
   with urllib.request.urlopen('http://127.0.0.1:8941/health',timeout=2) as response:
    if response.status==200:return process,log
  except Exception:pass
  time.sleep(.5)
 process.terminate();raise RuntimeError('Local translation server did not become ready')

def normalize(text):
 for a,b in [('June thirtieth, nineteen oh eight','30 June 1908'),('nineteen forty-nine','1949'),('twenty eleven','2011'),('seven seventy-five','775'),('seven seventy-seven','777')]:text=text.replace(a,b)
 return text.replace('each could belong to an invented world','each landscape could belong to an invented world')

def translate(cues,code):
 language,address=TARGETS[code];keys=[str(c['id']) for c in cues]
 schema={'type':'object','properties':{k:{'type':'string'} for k in keys},'required':keys,'additionalProperties':False}
 system=f'''You are a professional documentary translator. Translate the supplied English narration into fluent, idiomatic spoken {language}. Address the audience consistently using {address}. Preserve every factual claim, question, negation, uncertainty and scientific distinction. Do not summarize or add new claims. Return only the requested JSON object, with the same keys. Translate each paragraph as a coherent whole. Use ASCII digits for years and dates. Keep NASA and UNESCO unchanged. Keep place names in their normal local form or in the supplied Latin spelling.
Terminology: a geological basin is a depression in the landscape, not a swimming pool; a boulder is a large rock, never a person; friction is resistance between surfaces; a thaw slump is a collapsing slope caused by thawing ice-rich permafrost; permafrost is perennially frozen ground; timber is construction wood; tree rings are annual growth rings, not jewellery; basalt is volcanic rock; a mire is a peatland/wetland. 'Compelling' means fascinating, not compulsive. 'Tentative List' does not mean inscription on the World Heritage List. The narrative should sound natural and engaging, never like a literal machine translation.
Use this local-language glossary and correct grammar: {GLOSSARY[code]}'''
 body={'messages':[{'role':'system','content':system},{'role':'user','content':json.dumps({str(c['id']):normalize(c['text']) for c in cues},ensure_ascii=False)}],
       'temperature':.15,'top_p':.9,'max_tokens':3000,'seed':42,
       'response_format':{'type':'json_schema','json_schema':{'name':'translated_narration','strict':True,'schema':schema}}}
 request=urllib.request.Request('http://127.0.0.1:8941/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(request,timeout=900) as response:result=json.load(response)
 content=result['choices'][0]['message']['content'];data=json.loads(content)
 if set(data)!=set(keys) or not all(isinstance(v,str) and v.strip() for v in data.values()):raise ValueError('Translation did not retain every paragraph')
 for c in cues:
  for year in re.findall(r'\b(?:1949|2011|775|777|1908)\b',normalize(c['text'])):
   if year not in data[str(c['id'])]:raise ValueError('Missing year '+year+' in '+code+' cue '+str(c['id']))
 return data

def stamp(ms):
 seconds,millis=divmod(ms,1000);minutes,seconds=divmod(seconds,60);hours,minutes=divmod(minutes,60)
 return f'{hours:02}:{minutes:02}:{seconds:02},{millis:03}'

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--language',choices=list(TARGETS));parser.add_argument('--probe',action='store_true');parser.add_argument('--no-upload',action='store_true');args=parser.parse_args()
 process,log=prepare();out=Path('translated');out.mkdir(exist_ok=True)
 try:
  if args.probe:
   examples=[{'id':1,'text':'At Chara, the geological basin receives more rain than a true desert.'},
    {'id':2,'text':'The Hanging Stone is a granite boulder, not a person. Friction helps resist movement.'},
    {'id':3,'text':'Batagaika is a thaw slump caused by thawing ice-rich permafrost, not a meteorite crater.'},
    {'id':4,'text':'Researchers counted annual tree rings in construction timber, dating the start of Por-Bazhyn to the summer of 777.'}]
   result={code:translate(examples,code) for code in ['vi','es']}
   (out/'translation_probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
   print(json.dumps(result,ensure_ascii=False),flush=True)
  else:
   master=json.loads((ROOT/'master_timeline.json').read_text());rows=[]
   for chapter in master['chapters']:
    cues=[c for c in master['cues'] if c['chapter']==chapter['title']]
    result=translate(cues,args.language)
    rows.extend({**c,'source_text':c['text'],'text':result[str(c['id'])]} for c in cues)
    (out/(args.language+'.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Translated',args.language,chapter['title'],len(rows),'of 59 paragraphs',flush=True)
   assert len(rows)==59 and rows[-1]['end_ms']==1536000
   srt='\n\n'.join(str(c['id'])+'\n'+stamp(c['start_ms'])+' --> '+stamp(c['end_ms'])+'\n'+re.sub(r'\s+',' ',c['text']).strip() for c in rows)+'\n'
   (ROOT/'voices'/(args.language+'.srt')).write_text(srt,encoding='utf-8')
   (out/(args.language+'.txt')).write_text('\n\n'.join(c['text'] for c in rows),encoding='utf-8')
 finally:
  process.terminate();process.wait(timeout=30);log.close()
 if not args.no_upload:
  subprocess.run(['gh','release','upload','siberia-2536-production-v1',*[str(f) for f in out.iterdir()],
   '--repo',os.environ['GITHUB_REPOSITORY'],'--clobber'],check=True)

if __name__=='__main__':main()
