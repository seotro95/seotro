import csv,json,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
R=Path(__file__).parent
for n in ['graphics','overlays','delivery','scenes','review']:(R/n).mkdir(exist_ok=True)
A={x['label']:x for x in json.loads((R/'inventory.json').read_text())}
S=json.loads((R.parent/'package/SCENES_AND_PROMPTS.json').read_text());C=list(csv.DictReader(open(R.parent/'package/CHAPTERS_12.csv')))
F='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';B='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
bg=(10,24,32);fg=(242,238,224);gold=(226,182,111);muted=(162,187,193);teal=(111,190,199)
def font(n,b=False):return ImageFont.truetype(B if b else F,n)
def base(title,sub):
 im=Image.new('RGB',(1280,720),bg);d=ImageDraw.Draw(im);d.rectangle((48,44,54,124),fill=gold);d.text((75,40),title,font=font(30,True),fill=fg);d.text((77,94),sub,font=font(16),fill=muted);d.text((52,679),'YANA  /  EXPLANATORY VISUAL  /  NO MEASURED GENOMIC DATA',font=font(12),fill=muted);return im,d
def lines(d,xy,ls,size=21,gap=37,col=fg):
 for n,t in enumerate(ls):d.text((xy[0],xy[1]+n*gap),t,font=font(size),fill=col)
def save(im,name):im.save(R/'graphics'/f'{name}.png')
def cards(name,title,sub,data,foot=''):
 im,d=base(title,sub);width=(1138-24*(len(data)-1))/len(data)
 for n,(t,ls) in enumerate(data):
  x=70+n*(width+24);d.rounded_rectangle((x,211,x+width,529),radius=9,fill=(24,43,50));d.text((x+18,242),t,font=font(19,True),fill=gold);lines(d,(x+18,322),ls,19,36)
 if foot:d.text((75,596),foot,font=font(18),fill=fg)
 save(im,name)
def dashed(d,p,q):
 length=math.dist(p,q)
 for s in range(0,int(length),22):
  e=min(s+12,length);d.line((p[0]+(q[0]-p[0])*s/length,p[1]+(q[1]-p[1])*s/length,p[0]+(q[0]-p[0])*e/length,p[1]+(q[1]-p[1])*e/length),fill=teal,width=4)
def region(name,title,sub,ref,bounds,marks):
 im,d=base(title,sub);im.paste(Image.open(R.parent/'package/REFERENCES'/ref).resize((1170,453)),(55,168));d=ImageDraw.Draw(im)
 for lon,lat,t in marks:
  if lon<0:lon+=360
  x=55+(lon-bounds[0])/(bounds[1]-bounds[0])*1170;y=621-(lat-bounds[2])/(bounds[3]-bounds[2])*453
  d.ellipse((x-6,y-6,x+6,y+6),fill=gold);w=d.textlength(t,font=font(17,True));tx=max(65,min(x+12,1212-w));ty=max(175,min(y-29,589));d.rectangle((tx-5,ty-3,tx+w+5,ty+23),fill=bg);d.text((tx,ty),t,font=font(17,True),fill=fg)
 d.rectangle((0,650,1280,720),fill=bg);d.text((52,678),'MODERN GEOGRAPHIC ORIENTATION  /  NATURAL EARTH 1:110m  /  APPROXIMATE SITE REGIONS',font=font(12),fill=muted);save(im,name)
region('yana','YANA, ARCTIC SIBERIA','Human presence approximately 31,600 years ago','YANA_MODERN_BASE.png',(95,180,48,80),[(135.4,70.7,'YANA RHS'),(142,75.8,'LAPTEV SEA')])
region('yana_malta','YANA AND MAL\'TA','Different places and dates within a wider northern Eurasian history','YANA_MALTA_MODERN_BASE.png',(85,180,45,80),[(135.4,70.7,'YANA  /  ~31,600 YEARS'),(103.5,52.85,"MAL'TA  /  ~24,000 YEARS")])
region('kolyma','A MUCH LATER COMPARISON','Kolyma-region ancient DNA: approximately 9,800 years old','YANA_KOLYMA_MODERN_BASE.png',(120,180,55,80),[(135.4,70.7,'YANA  /  ~31,600 YEARS'),(160,67,'KOLYMA REGION  /  ~9,800 YEARS')])
region('pacific','A WIDER NORTHERN WORLD','Related inheritance does not identify a complete migration route','NORTH_PACIFIC_MODERN_BASE.png',(45,285,20,82),[(135.4,70.7,'YANA'),(103.5,52.85,"MAL'TA"),(211,63,'ALASKA'),(245,42,'NORTH AMERICA')])
im,d=base('BERINGIA: GEOGRAPHIC CONTEXT','Lower sea levels exposed broad lands between northeastern Asia and Alaska');p=ImageOps.contain(Image.open(R.parent/'package/REFERENCES/NPS_BERINGIA_BATHYMETRY_REFERENCE.png').convert('RGB'),(1170,447));im.paste(p,((1280-p.width)//2,160));d.text((66,623),'NPS reference: approximately 21,000 BP. Not the coastline of Yana at 31,600 years ago.',font=font(17),fill=fg);d.rectangle((0,661,1280,720),fill=bg);d.text((52,679),'SOURCE: U.S. NATIONAL PARK SERVICE  /  ORIGINAL MAP LABELS RETAINED',font=font(12),fill=muted);save(im,'beringia')
cards('methods','THREE RECORDS. DIFFERENT QUESTIONS.','Stronger explanations bring independent kinds of evidence together',[('ARCHAEOLOGY',['Objects and working traces','Context in the ground']),('ENVIRONMENT',['Plants, animals, sediments','Changing local conditions']),('ANCIENT DNA',['Inherited variation','Comparisons between samples'])])
cards('objects','MATERIALS AND SKILLED WORK','Objects at Yana preserve different parts of human activity',[('WORKED HORN',['A remarkable shaped object','Part of the site\'s name']),('IVORY AND BONE',['Manufacture and repair','Practical choices']),('STONE AND ORNAMENTS',['Durable surviving traces','Meaning is not automatic'])],'Generic replicas in the film are not the original Yana collection.')
im,d=base('DAMAGED, MIXED, INCOMPLETE','Ancient DNA fragments require authentication and careful comparison')
for row in range(5):
 for k in range(6):
  x=80+k*91+(row%2)*25;y=204+row*66;length=47+k%3*10;d.rounded_rectangle((x,y,x+length,y+16),radius=5,fill=teal);d.rectangle((x,y,x+7,y+16),fill=gold)
lines(d,(775,213),['Short surviving fragments','','Damage near fragment ends','','Possible modern contamination','','Controls and comparisons'],20,41);d.text((82,593),'Colours explain a concept; they do not establish a molecule\'s age.',font=font(19),fill=fg);save(im,'damage')
cards('auth','ASK WHAT ELSE COULD PRODUCE THE RESULT','Good analysis distinguishes superficially similar possibilities',[('INHERITED VARIATION',['A signal from ancient people','Tested by comparisons']),('CONTAMINATION',['Material introduced later','Controlled and investigated']),('READING ERROR',['Error during analysis','Tested with other evidence'])])
im,d=base('PATTERNS ACROSS MANY POSITIONS','A teaching diagram, not actual Yana sequences or measured ancestry proportions')
for row in range(3):
 y=230+row*111;d.text((75,y+13),f'COMPARISON {row+1}',font=font(17),fill=fg)
 for k in range(16):d.rectangle((301+k*52,y,341+k*52,y+45),fill=[teal,gold,(148,160,160)][(k//3+(row if k%5==0 else 0))%3])
d.text((80,608),'Repeated sharing patterns can constrain relationships.',font=font(22),fill=fg);save(im,'variants')
im,d=base('INHERITANCE ACROSS GENERATIONS','A simplified teaching model; these are not actual family genomes')
for row,(y,t) in enumerate([(229,'ONE PARENT'),(366,'OTHER PARENT'),(511,'DESCENDANT')]):
 d.text((82,y+3),t,font=font(19,True),fill=gold)
 for k in range(10):d.rounded_rectangle((334+k*70,y,385+k*70,y+35),radius=5,fill=teal if (k+row)%3 else gold)
d.text((335,593),'Recombination reshuffles inherited segments.',font=font(22),fill=fg);save(im,'inheritance')
cards('models','A FITTING MODEL IS NOT A COMPLETE PAST','Assumptions, alternative explanations and missing samples still matter',[('AVAILABLE SAMPLES',['Which observations fit?','How much data survives?']),('ALTERNATIVES',['What else could fit?','What might disprove it?']),('NEW EVIDENCE',['Additional ancient genomes','May revise the relationships'])])
cards('missing','KEEP THE UNSAMPLED PAST VISIBLE','An empty place in a dataset is not an empty place in human history',[('SURVIVING EVIDENCE',['A limited set of samples','Uneven preservation']),('MISSING EVIDENCE',['Other people and places','Not directly represented']),('FUTURE COMPARISONS',['Test new relationships','Revise existing explanations'])])
im,d=base('RELATED HISTORIES, DIFFERENT SAMPLES','Comparisons constrain population relationships; lines do not indicate journeys')
for x,t,sub in [(245,'YANA','~31,600 years ago'),(640,"MAL'TA",'~24,000 years ago'),(1035,'LATER SAMPLES','Different times and places')]:
 d.ellipse((x-21,268,x+21,310),fill=gold);d.text((x-d.textlength(t,font=font(22,True))/2,350),t,font=font(22,True),fill=fg);d.text((x-d.textlength(sub,font=font(18))/2,398),sub,font=font(18),fill=muted)
dashed(d,(270,290),(615,290));dashed(d,(665,290),(1010,290));lines(d,(168,515),['Related does not mean identical, directly ancestral,','or part of one identified travelling group.'],24,40);save(im,'network')
cards('labels','SCIENTIFIC GROUPINGS, NOT RECOVERED TRIBAL NAMES','Names organise comparisons; they do not recover a complete cultural identity',[('ANCIENT NORTH SIBERIANS',['Represented by Yana samples','A model-based grouping']),('LATER COMPARISONS',['Ancient Palaeo-Siberians','Neo-Siberians']),('KEEP TIME VISIBLE',['Different samples and periods','Not an unchanged population'])])
cards('two_samples','TWO SAMPLES, A MUCH LARGER QUESTION','The 2019 study tested particular genetic relationships',[('OBSERVATIONS',['Not close genetic relatives','No tested recent inbreeding']),('LIMITS',['Not a complete guest list','Not every social relationship'])],'Two surviving genomes do not reveal every member of a community.')
cards('effective','EFFECTIVE POPULATION SIZE IS NOT A CENSUS','A technical genetic estimate depends on a demographic model',[('GENETIC HISTORY',['Inheritance and reproduction','Model assumptions matter']),('HEADCOUNT',['People alive at one time','People beside a particular fire'])],'No precise village population is reconstructed here.')
im,d=base('TIME BETWEEN THE SAMPLES MATTERS','Approximate sample ages, not one household or an unbroken lineage');d.line((117,352,1162,352),fill=muted,width=3)
for age,t in [(31600,'YANA'),(24000,"MAL'TA"),(9800,'KOLYMA REGION')]:
 x=150+(33000-age)/(33000-9000)*980;d.ellipse((x-8,344,x+8,360),fill=gold);d.text((x-d.textlength(t,font=font(22,True))/2,260),t,font=font(22,True),fill=fg);sub=f'~{age:,} years ago';d.text((x-d.textlength(sub,font=font(20))/2,403),sub,font=font(20),fill=fg)
d.text((160,554),'Older',font=font(20),fill=muted);d.text((1071,554),'Younger',font=font(20),fill=muted);save(im,'time')
cards('time_change','YANA PRECEDES THE LAST GLACIAL MAXIMUM','There was no single unchanging ice-age landscape',[('YANA SAMPLES',['Approximately 31,600 years old','Earlier northern occupation']),('LATER ENVIRONMENTS',['Ice, climate and sea level','Changing habitats and resources'])],'A map for one period cannot stand for every other period.')
cards('limits','A GENETIC CONNECTION IS NOT A TRAVEL DIARY','Different evidence is needed for routes, dates and activity',[('INHERITED RELATIONSHIP',['Shared genetic patterns','Across many generations']),('GEOGRAPHIC JOURNEY',['Where people moved','When, and under what conditions'])],'The Yana samples do not identify direct founders of all Indigenous Americans.')
cards('change','POPULATION CHANGE IS NOT A READY-MADE MOVIE','Different historical processes can produce related genetic patterns',[('WHAT MODELS TEST',['Relationships across time','Patterns in sampled genomes']),('WHAT THEY DO NOT FILM',['An identified conquest','One complete personal journey'])],'Chronology, archaeology and additional genomes help constrain explanations.')
cards('identity','PEOPLE ARE MORE THAN RESEARCH SAMPLES','A selective scientific record does not preserve a whole person',[('WHAT MAY SURVIVE',['Objects and context','Some inherited relationships']),('WHAT IS NOT RECOVERED',['Every name and conversation','A complete cultural identity'])],'Genetic ancestry alone does not decide a living community\'s identity.')
# Embedded suffixes are candidate prompt locators. Selection below follows visual review.
labels={x['inferred_prompt_id']:x['label'] for x in A.values()}
labels.update({2:'@yana',6:'@limits',8:'@methods',12:'@yana',15:'V409',19:'V418',34:'@damage',38:'V443',40:'@damage',42:'@auth',43:'@auth',45:'@variants',46:'@variants',48:'V484',49:'@inheritance',51:'@models',54:'@missing',57:'@labels',58:'@pacific',60:'@labels',63:'@missing',64:'V425',67:'@two_samples',70:'@effective',71:'@effective',77:'@yana_malta',78:'@network',79:'V480',85:'V409',86:'@time_change',87:'V446',89:'@labels',90:'@labels',92:'@change',93:'@methods',95:'@beringia',98:'@limits',99:'@pacific',100:'@time_change',105:'@identity',117:'V467',119:'@pacific'})
def seg(label,d=10,source=0,crop=1):return dict(label=label,duration=d,source_in=source,crop=crop)
plan=[]
for s in S:
 chapter=next(int(c['chapter']) for c in C if int(c['start_seconds'])<=s['start_seconds']<int(c['end_seconds']))
 plan.append(dict(cue=s['id'],start=s['start_seconds'],end=s['end_seconds'],voice_en=s['voice_en'],transition='cut',segments=[seg(labels[s['clip_id']])],chapter=chapter,chapter_overlay='',lower_overlay=''))
# Twelve purposeful shots in the existing first30seconds. Voice timing is untouched.
plan[0]['segments']=[seg('V403',3),seg('V456',2,.3),seg('V409',2.5,.5),seg('V415',2.5,1)]
plan[1]['segments']=[seg('@yana',2.5),seg('V420',2.5,.5),seg('V418',2.5,.3),seg('V406',2.5,.5)]
plan[2]['segments']=[seg('V405',2.5,.5),seg('V407',2.5,.3),seg('@variants',2.5),seg('@network',2.5)]
overrides={13:'@yana',18:'V409',26:'V426',36:'V456',37:'@damage',41:'V443',43:'@damage',45:'@auth',46:'@auth',49:'@variants',50:'@variants',52:'V484',53:'@inheritance',55:'@models',58:'@missing',62:'@labels',63:'@pacific',65:'@labels',68:'@missing',69:'V425',73:'@two_samples',76:'@effective',77:'@effective',78:'@effective',84:'@yana_malta',85:'@time',86:'@network',90:'@limits',95:'@time_change',97:'V446',99:'@labels',100:'@labels',101:'@kolyma',102:'@time',103:'@change',104:'@methods',106:'@beringia',110:'@limits',111:'@pacific',112:'@time_change',118:'@identity',133:'V467',136:'@pacific'}
for cue,label in overrides.items():plan[cue-1]['segments']=[seg(label)]
cutaways={4:'V456',5:'V425',6:'V456',7:'V467',8:'V411',9:'V428',10:'@methods',11:'V424',12:'V407',14:'V425',15:'V409',16:'V415',17:'V420',18:'V416',19:'V416',20:'V423',21:'V467',22:'V475',23:'V423',24:'V427',25:'V428',26:'@objects',27:'V433',28:'V412',29:'V430',30:'V424',31:'V430',32:'V506',33:'V432',34:'V424',35:'V502',36:'V403',37:'V405',38:'@damage',39:'V484',40:'@damage',41:'V441',42:'V446',43:'V405',44:'@auth',45:'V444',46:'V443',47:'V508',48:'@variants',49:'V405',50:'V447',51:'@variants',52:'V455',53:'V451',54:'@inheritance',55:'V453',56:'@models',57:'V466',58:'V455',59:'V403',60:'@network',61:'V443',62:'V456',63:'V467',64:'@identity',65:'V461',66:'V438',67:'@missing',68:'V464',69:'V428',70:'@missing',71:'V418',72:'@two_samples',73:'V456',74:'V475',75:'@two_samples',76:'V413',77:'V453',78:'V470',79:'V422',80:'V475',81:'V424',82:'@methods',83:'V411',84:'@time',85:'V456',86:'V477',87:'@network',88:'@network',89:'@two_samples',90:'V484',91:'@network',92:'@missing',93:'@yana_malta',94:'V415',95:'@time',96:'V420',97:'V487',98:'V428',99:'@time',100:'V485',101:'@time',102:'V485',103:'V491',104:'V477',105:'V425',106:'@pacific',107:'V423',108:'@time',109:'@network',110:'@two_samples',111:'V456',112:'@beringia',113:'V475',114:'V409',115:'@missing',116:'V403',117:'V424',118:'V475',119:'V405',120:'V423',121:'V475',122:'V432',123:'V424',124:'V456',125:'V428',126:'@models',127:'@network',128:'V456',129:'V437',130:'V424',131:'V506',132:'@methods',133:'V505',134:'@time_change',135:'@variants',136:'@yana',137:'V415',138:'V501'}
for cue,other in cutaways.items():
 p=plan[cue-1];primary=p['segments'][0]['label']
 if primary!=other:p['segments']=[seg(primary,6),seg(other,4,1 if not other.startswith('@') else 0)]
# Avoid unverified small background figures by using close, temporally reviewed portions.
for p in plan:
 if len(p['segments'])==1 and p['segments'][0]['label'] in ['V406','V413','V469','V495','V505']:
  p['segments']=[seg(p['segments'][0]['label'],6),seg('V475',4,1)]
for cue,a,b in [(12,'V403','V407'),(24,'V415','V427'),(72,'V456','V467'),(94,'V409','V415'),(127,'V510','V456'),(138,'V403','V501')]:
 plan[cue-1].update(transition='dissolve',segments=[seg(a,5.3),seg(b,5.3,1)])
rejected=['V415','V418','V467','V404','V414','V417','V421','V436','V440','V442','V445','V448','V450','V452','V458','V459','V465','V471','V472','V478','V479','V486','V488','V489','V492','V494','V497','V498','V503','V515']
# All charts that could be mistaken for measured results are replaced, including cutaways.
replacement={'V440':'@variants','V448':'@variants','V450':'V484','V452':'@models','V465':'V425','V492':'@methods','V494':'@beringia','V498':'@time_change','V503':'V415','V515':'V467'}
for p in plan:
 for x in p['segments']:
  if x['label']=='V415':x['label']='V420'
  if x['label']=='V418':x['label']='V469'
  if x['label']=='V467':x['label']={0:'V413',1:'V495',2:'V473'}[p['cue']%3]
  if x['label'] in replacement:x['label']=replacement[x['label']];x['source_in']=0
  assert x['label'] not in rejected,x
  assert x['label'].startswith('@') or x['label'] in A
  assert x['duration']+x['source_in']<=10.0001 or x['label'].startswith('@')
 assert abs(sum(x['duration'] for x in p['segments'])-(10.6 if p['transition']=='dissolve' else 10))<.001
 cue=p['cue'];chapter=C[p['chapter']-1];im=Image.new('RGBA',(1280,720));d=ImageDraw.Draw(im);drawn=False
 if cue==2:
  d.rounded_rectangle((44,494,600,636),radius=5,fill=(*bg,218));d.rectangle((44,494,49,636),fill=(*gold,255));d.text((71,512),'YANA',font=font(40,True),fill=(*fg,255));d.text((73,575),'ARCTIC SIBERIA  /  ~31,600 YEARS AGO',font=font(19),fill=(*gold,255));drawn=True
 elif p['start']==int(chapter['start_seconds']) and cue>3:
  t=chapter['title_en'].upper();size=21
  while d.textlength(t,font=font(size,True))>1090:size-=1
  w=d.textlength(t,font=font(size,True));d.rounded_rectangle((48,38,min(1232,94+w),117),radius=5,fill=(*bg,218));d.rectangle((48,38,53,117),fill=(*gold,255));d.text((70,49),f"{p['chapter']:02d} / YANA",font=font(11),fill=(*gold,255));d.text((70,75),t,font=font(size,True),fill=(*fg,255));drawn=True
 if drawn and not p['segments'][0]['label'].startswith('@'):
  dest=R/'overlays'/f'{cue:03d}.png';im.save(dest);p['chapter_overlay']=str(dest)
 captions={1:'Illustrative tooth replicas, not the original Yana specimens',4:'Adult community reconstruction; not the owners of the recovered teeth',20:'Illustrative camp activity; no identified conversation or individuals',25:'Yana RHS discovered in 2001  /  Illustrative field scene',26:'Worked horn, ivory, bone and stone  /  Generic replicas',29:'Replica objects; original social meanings remain uncertain',31:'An anonymous adult maker, not an identified ancient person',36:'Two fragmented milk teeth; their owners are not reconstructed',39:'Paper analogy, not the laboratory procedure',54:'Teaching analogy, not measured Yana genomes',61:'Sikora and colleagues, Nature, 2019',64:'Genetic relationships do not assign modern nationality',66:'Object-sorting analogy; not genetic measurement',71:'Human presence around 31,600 years ago; not a first-arrival date everywhere',74:'Illustrative adult community; no reconstructed population headcount',80:'Illustrative contacts, not a demonstrated Yana journey',81:'Exchange of objects and inheritance follow different processes',87:'Tree analogy only; rings shown are not sample-dating measurements',91:'An older related sample is not automatically a direct ancestor',98:'Illustrative stratigraphic work, not original footage of Yana excavation',107:'Practical travel conditions; not an identified migration route',108:'Yana does not date the first arrival in the Americas',119:'Illustrative documentation and laboratory handling',121:'Anonymous adults demonstrating practical collaboration',128:'Tooth replicas; the recovered individuals are not pictured',129:'Illustrative preservation context, not original excavation footage',137:'Conceptual juxtaposition of objects and landscape'}
 if cue in captions:
  im=Image.new('RGBA',(1280,720));d=ImageDraw.Draw(im);t=captions[cue];size=16
  while d.textlength(t,font=font(size))>1134:size-=1
  w=d.textlength(t,font=font(size));d.rounded_rectangle((48,609,82+w,659),radius=5,fill=(*bg,219));d.rectangle((48,609,52,659),fill=(*gold,255));d.text((65,625),t,font=font(size),fill=(*fg,255));dest=R/'overlays'/f'lower_{cue:03d}.png';im.save(dest);p['lower_overlay']=str(dest)
(R/'EDIT_PLAN.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
with (R/'delivery/EDIT_TIMELINE.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['cue','start_seconds','end_seconds','transition','shot','source_label','source_file','source_in','duration','voice_en'])
 for p in plan:
  for n,x in enumerate(p['segments'],1):w.writerow([p['cue'],p['start'],p['end'],p['transition'],n,x['label'],str(R/'graphics'/f"{x['label'][1:]}.png") if x['label'].startswith('@') else A[x['label']]['name'],x['source_in'],x['duration'],p['voice_en']])
summary=json.loads((R/'INVENTORY_SUMMARY.json').read_text());summary.update(rejected_source_labels=rejected,opening_shots=sum(len(p['segments']) for p in plan[:3]),planned_shots=sum(len(p['segments']) for p in plan),graphic_count=len(list((R/'graphics').glob('*.png'))),used_source_clips=len({x['label'] for p in plan for x in p['segments'] if not x['label'].startswith('@')}),no_children_policy='Only inspected adult scenes; ambiguous small figures and modern-camp scene V515 excluded.',english_reference_sha256='7014702fdb86744e8ddbf8a74eb7ef176bbb4cb9865aaf4e0e7931e27ae0047c',audio='Original English narration only; no source audio, music or SFX.',source_selection='All115 unique sources inspected via contact sheets;13 adult group scenes additionally sampled at0.6,4.5,8.8seconds; no continuous manual viewing claim.',reason='Generated geography, invented measured charts, embedded logos/text, small background figures in river panorama V415, modern notebooks/magnifiers in ancient camp scenes, modern camp equipment or ambiguous small figures are excluded; five missing prompt contexts covered by inspected alternatives and explanatory graphics.')
(R/'EDITOR_DECISIONS.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary),flush=True)
