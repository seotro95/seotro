import csv,json,re,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).parent;P=R.parent/'package';F='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';B='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
for n in ['graphics','overlays','delivery','review']:(R/n).mkdir(exist_ok=True)
bg=(10,24,32);fg=(243,239,225);gold=(226,182,111);muted=(164,190,196);teal=(111,190,199)
def ft(n,b=False):return ImageFont.truetype(B if b else F,n)
def wrap(d,t,width,font):
 out=[];line=''
 for w in t.split():
  if line and d.textlength(line+' '+w,font=font)>width:out.append(line);line=''
  line=(line+' '+w).strip()
 if line:out.append(line)
 return out

def base(title,sub,footer='DENISOVA / EXPLANATORY GRAPHIC / NOT MEASURED GENOMIC DATA'):
 im=Image.new('RGB',(1280,720),bg);d=ImageDraw.Draw(im);size=31
 while d.textlength(title,font=ft(size,True))>1128:size-=1
 d.rectangle((48,35,54,119),fill=gold);d.text((77,32),title,font=ft(size,True),fill=fg)
 for i,t in enumerate(wrap(d,sub,1130,ft(17))[:2]):d.text((79,82+i*25),t,font=ft(17),fill=muted)
 d.text((49,691),footer,font=ft(11),fill=muted);return im,d

def save(im,name):im.save(R/'graphics'/f'{name}.png')
def cards(name,title,sub,data,foot=''):
 im,d=base(title,sub);n=len(data);w=(1140-22*(n-1))/n
 for k,(head,ls) in enumerate(data):
  x=70+k*(w+22);d.rounded_rectangle((x,196,x+w,548),radius=10,fill=(24,43,50));y=221
  for t in wrap(d,head,w-36,ft(21,True)):d.text((x+18,y),t,font=ft(21,True),fill=gold);y+=29
  y=max(y+28,311)
  for t in ls:
   for line in wrap(d,t,w-36,ft(19)):d.text((x+18,y),line,font=ft(19),fill=fg);y+=30
   y+=14
 if foot:
  for i,t in enumerate(wrap(d,foot,1120,ft(19))[:2]):d.text((77,590+i*30),t,font=ft(19),fill=fg)
 save(im,name)
guide=json.load(open(P/'REFERENCES/REFERENCE_GUIDE.json'))
def mapplate(name,title,sub,ref,marks):
 im,d=base(title,sub,'MODERN GEOGRAPHIC ORIENTATION / NATURAL EARTH 1:110m / APPROXIMATE REGIONS')
 im.paste(Image.open(P/'REFERENCES'/f'{ref}.png').convert('RGB').resize((960,540)),(160,132));d=ImageDraw.Draw(im);bounds=guide['map_bounds'][ref]
 for lon,lat,label in marks:
  x=160+(lon-bounds[0])/(bounds[1]-bounds[0])*960;y=672-(lat-bounds[2])/(bounds[3]-bounds[2])*540
  d.ellipse((x-5,y-5,x+5,y+5),fill=gold);w=d.textlength(label,font=ft(15,True));tx=max(170,min(x+10,1110-w));ty=max(140,min(y-27,635));d.rounded_rectangle((tx-5,ty-4,tx+w+5,ty+22),radius=3,fill=bg);d.text((tx,ty),label,font=ft(15,True),fill=fg)
 save(im,name)
altai=(84.7,51.4,'DENISOVA / ALTAI');baishiya=(102.6,35.5,'BAISHIYA / XIAHE');harbin=(126.6,45.8,'HARBIN');penghu=(120,23.5,'TAIWAN STRAIT / PENGHU')
mapplate('asia','A SMALL CLUE. A MUCH WIDER QUESTION.','Find regions for comparison, not a demonstrated migration route','ASIA_MODERN_BASE',[altai,baishiya,harbin,penghu])
mapplate('altai','DENISOVA CAVE / SOUTHERN SIBERIA','The Altai setting differs from the far northern Yana landscape','ALTAI_MODERN_BASE',[altai])
mapplate('oceania','BEYOND ONE SIBERIAN REFERENCE','Denisovan-related ancestry varies across living populations','ASIA_OCEANIA_MODERN_BASE',[altai])
mapplate('plateau','THE TIBETAN PLATEAU CONNECTION','Baishiya Karst Cave and the Xiahe mandible','TIBETAN_PLATEAU_MODERN_BASE',[baishiya])
mapplate('taiwan','PENGHU / TAIWAN STRAIT','A broad find region; no exact dredging position or ancient coastline is reconstructed','ASIA_MODERN_BASE',[penghu])
mapplate('harbin_map','HARBIN / NORTHEASTERN CHINA','Two molecular approaches reported a Denisovan connection in 2025','ASIA_MODERN_BASE',[harbin])
cards('methods','DIFFERENT EVIDENCE. CONNECTED QUESTIONS.','Each record contributes something different',[('ARCHAEOLOGY',['Objects and working traces','Position and context']),('DNA',['Inherited variation','Comparisons between genomes']),('PROTEINS',['Surviving amino-acid sequences','Another route to fossil comparisons'])])
cards('identity','PEOPLE WERE MORE THAN THEIR SAMPLES','A scientific comparison cannot recover a complete personal life',[('WHAT MAY SURVIVE',['Some inherited relationships','Objects and context']),('WHAT IS NOT RECOVERED',['Every name and conversation','A verified face or whole identity'])])
cards('time','DISCOVERY YEAR IS NOT FOSSIL AGE','Different dates answer different questions',[('2008',['Modern excavation discovery','A fragment enters the collection']),('2010',['Molecular reports published','The comparison changes']),('ANCIENT AGE',['Estimated from evidence','Ranges and uncertainty matter'])],'An age interval is not an exact meeting date or a personal birthday.')
cards('association','NEARBY DOES NOT MEAN PERSONALLY OWNED','Objects and bones can raise different questions',[('ARCHAEOLOGICAL CONTEXT',['Where was it found?','How are deposits associated?']),('AN INDIVIDUAL LIFE',['Who made or owned it?','Different supporting evidence is needed'])])
cards('auth','TEST THE ALTERNATIVE EXPLANATIONS','A plausible signal still needs authentication',[('ANCIENT MATERIAL',['Surviving fragments','Characteristic damage']),('LATER CONTAMINATION',['Microbes or handling','Controls and comparisons']),('READING ERRORS',['Sequencing uncertainty','Independent checks'])])
im,d=base('DAMAGED MOLECULES. CAREFUL COMPARISONS.','Conceptual fragments; these are not measured Denisovan sequences')
for row in range(5):
 for col in range(7):
  x=75+col*88+(row%2)*22;y=195+row*67;d.rounded_rectangle((x,y,x+52+col%3*6,y+17),radius=5,fill=teal);d.rectangle((x,y,x+6,y+17),fill=gold)
for k,t in enumerate(['Short surviving fragments','Chemical damage','Possible contamination','Controls and comparisons']):d.text((775,215+k*78),t,font=ft(20),fill=fg)
d.text((80,592),'No single visual feature is an infallible seal of authenticity.',font=ft(21),fill=fg);save(im,'damage')
cards('mt_nuclear','TWO REPORTS. DIFFERENT SCALES.','Both published in 2010; they did not provide identical information',[('MITOCHONDRIAL DNA',['A small separate genome','Usually follows the maternal line']),('NUCLEAR DNA',['A much larger genetic record','Broader inherited comparisons'])],'One maternal lineage is not the whole of an individual\'s ancestry.')
im,d=base('COVERAGE: REPEATED READS OF GENOMIC POSITIONS','The 2012 Denisovan genome was reported at about thirtyfold average coverage')
for row in range(8):
 y=205+row*37
 for k in range(14):d.rounded_rectangle((79+k*51+(row%2)*12,y,115+k*51+(row%2)*12,y+13),radius=4,fill=teal if (k+row)%4 else gold)
d.text((858,229),'~30x',font=ft(71,True),fill=gold);d.text((816,328),'AVERAGE COVERAGE',font=ft(17,True),fill=fg)
for k,t in enumerate(['Repeated sequence reads','Not thirty sampled people','Uneven certainty can remain']):d.text((780,389+k*45),t,font=ft(18),fill=fg)
d.text((81,594),'Simplified teaching rows; not a plot of the original sequencing data.',font=ft(19),fill=fg);save(im,'coverage')
cards('one_genome','ONE GENOME. ONE SAMPLED INDIVIDUAL.','More information from one sample is not a census',[('DEEPER INFORMATION',['More repeated reads','More detailed comparisons']),('A LARGER POPULATION',['Other people and places','Still incompletely sampled'])])
cards('missing','KEEP THE UNSAMPLED PAST VISIBLE','A sharper reference sample is not a complete history of Asia',[('SAMPLES THAT SURVIVED',['A limited record','Uneven preservation']),('MISSING COMPARISONS',['Other places and generations','May alter the model'])])
im,d=base('INHERITED SEGMENTS CAN SURVIVE','A teaching model of reshuffling, not measured ancestry proportions')
for row,(y,t) in enumerate([(223,'EARLIER GENERATION'),(365,'LATER GENERATION'),(507,'LIVING GENOMES')]):
 d.text((70,y+5),t,font=ft(17,True),fill=gold)
 for k in range(11):d.rounded_rectangle((352+k*66,y,399+k*66,y+31),radius=4,fill=gold if (k+row)%4==0 else teal)
d.text((351,595),'A surviving segment is not a complete ancient genome.',font=ft(20),fill=fg);save(im,'inheritance')
cards('epas','EPAS1: ONE PART OF A LARGER EXPLANATION','A region involved in the body\'s response to low oxygen at altitude',[('INHERITED VARIATION',['A Tibetan-region example','A Denisovan-related connection reported in 2014']),('BIOLOGY AND ENVIRONMENT',['Many interacting factors','Not one gene explaining all abilities'])],'An inherited relationship does not establish the Altai individual\'s own biography.')
cards('proteins','PROTEINS OPEN ANOTHER MOLECULAR WINDOW','Surviving sequences can support comparisons when useful DNA is scarce',[('SCREENING',['Collagen fingerprints','Find promising fragments']),('IDENTIFICATION',['Diagnostic sequences','Test a narrower lineage question'])],'Identifying a human fragment is not automatically identifying a Denisovan one.')
cards('minimum_age','XIAHE: A LOWER AGE BOUND','The 2019 report linked the mandible to Denisovans through ancient proteins',[('ABOUT 160,000 YEARS',['Minimum age from carbonate crust','The fossil may be older']),('WHAT THAT DOES NOT DATE',['No exact death date','No complete personal life history'])])
cards('sediment','MOLECULAR CLUES IN THE GROUND','Sediment DNA widens the record beyond a few recognised bones',[('WHAT IT CAN ADD',['Evidence of past human groups','Context across deposits']),('WHAT STILL MATTERS',['Deposition and sampling','Chronology and interpretation'])],'Sediment DNA is not automatically one named person or a complete individual genome.')
cards('baishiya','ONE CAVE. SEVERAL KINDS OF EVIDENCE.','Baishiya Karst Cave on the Tibetan Plateau',[('2019',['Xiahe mandible','Ancient protein comparison']),('2020',['Sediment DNA','A separate molecular record']),('2024',['Rib fragment','Proteins and wider archaeology'])])
cards('parentage','DENISOVA 11 / FIRST-GENERATION PARENTAGE','The genome studied in 2018 indicated these parental relationships',[('ONE PARENT',['Neanderthal mother']),('OTHER PARENT',['Denisovan father'])],'No portraits, meeting scene or personal biography are reconstructed.')
cards('labels','A RESEARCH LABEL IS NOT A COMPLETE PEOPLE','A diverse history cannot be reduced to one face or costume',[('DENISOVAN',['A name drawn from the cave','Used in scientific comparisons']),('KEEP THE LIMITS VISIBLE',['Different places and periods','No recovered tribal self-name'])])
cards('map_key','WHAT DOES A LINE ON A MAP MEAN?','A research comparison, a proposed movement and a documented journey are different',[('OBSERVED LOCATIONS',['Fossils anchor observations','A site is not a complete route']),('MISSING HISTORY',['Other places may be unsampled','No migration path is asserted here'])])
cards('penghu','PENGHU / A NEW PROTEIN CONNECTION','The 2025 study linked the Taiwan Strait mandible with a male Denisovan',[('WHAT THE MOLECULES ADDED',['A lineage comparison','Anatomy becomes more informative']),('DATING REMAINS DIFFICULT',['Alternative age intervals','No invented exact fossil age'])])
cards('harbin','HARBIN / TWO MOLECULAR APPROACHES','Studies reported in 2025 supported a Denisovan connection',[('ANCIENT PROTEINS',['Sequences from the cranium','An independent kind of comparison']),('MITOCHONDRIAL DNA',['Recovered from dental calculus','A minimum age of 146,000 years'])],'One individual does not provide a universal Denisovan portrait.')
cards('taxonomy','MOLECULAR RELATIONSHIP AND TAXONOMIC NAMES','Names such as Homo longi remain part of a wider scientific discussion',[('MOLECULAR EVIDENCE',['Supports a relationship','Adds a kind of comparison']),('NAMING AND VARIATION',['How should groups be described?','Not automatically settled by one result'])])
cards('new2026','MORE FRAGMENTS. WIDER QUESTIONS.','Primary studies published in September and October 2026',[('BIANFU / SOUTHWEST CHINA',['Protein-linked human remains','Anatomy and archaeological context']),('XUJIAYAO / NORTH CHINA',['Ancient protein evidence','Denisovan affiliation and wider comparisons'])],'Shared features do not imply identical appearance across all places and times.')
cards('xujiayao','XUJIAYAO / NORTHERN CHINA','Protein research published in October 2026',[('A WIDER COMPARISON',['Results supported Denisovan affiliation','Anatomical comparisons can expand']),('KEEP VARIATION VISIBLE',['New questions about diversity','No single universal appearance'])])
S=json.load(open(P/'SCENES_AND_PROMPTS.json'));C=list(csv.DictReader(open(P/'CHAPTERS_12.csv')));assets={x['label']:x for x in json.load(open(R/'inventory.json'))}
primary={x['id']:x['filename'][:-4] for x in S}
replacements={3:'@asia',5:'@asia',11:'@altai',12:'DE06_010',13:'DE06_069',14:'DE06_013',15:'DE06_020',16:'@time',17:'@time',18:'@time',19:'DE06_018',20:'@association',21:'DE06_013',22:'DE06_024',23:'@damage',25:'@damage',26:'DE06_024',28:'DE06_026',29:'DE06_027',30:'@methods',31:'@auth',33:'@mt_nuclear',34:'@mt_nuclear',35:'DE06_028',36:'@mt_nuclear',37:'DE06_026',38:'@missing',39:'DE06_036',40:'@labels',42:'@altai',43:'@methods',45:'@coverage',46:'@coverage',47:'@coverage',48:'DE06_001',49:'@one_genome',50:'DE06_046',51:'@asia',52:'@missing',55:'@inheritance',56:'@oceania',57:'@inheritance',58:'@identity',60:'@missing',61:'@asia',62:'@epas',63:'@plateau',64:'@epas',65:'@epas',66:'DE06_062',67:'DE06_060',68:'@proteins',69:'@proteins',70:'@plateau',71:'@minimum_age',72:'@asia',73:'@methods',76:'DE06_069',77:'DE06_071',78:'@sediment',79:'@sediment',80:'@plateau',81:'@baishiya',82:'DE06_074',83:'DE06_075',84:'DE06_076',85:'@methods',86:'DE06_081',87:'@parentage',88:'@parentage',89:'@parentage',90:'@inheritance',91:'@labels',92:'@asia',93:'@map_key',94:'@asia',95:'DE06_094',96:'DE06_081',97:'DE06_088',98:'@penghu',99:'@penghu',100:'@harbin_map',101:'@harbin',102:'@identity',103:'@taxonomy',104:'DE06_090',105:'DE06_093',106:'@new2026',107:'@new2026',108:'DE06_096',109:'DE06_097',110:'@association',111:'@xujiayao',112:'DE06_098',113:'@asia',114:'DE06_101',115:'DE06_102',116:'@methods',117:'DE06_104',118:'DE06_076',119:'DE06_106',120:'DE06_109',121:'DE06_001',123:'@asia',124:'@identity',126:'DE06_110',6:'@methods',7:'@identity',8:'DE06_014',9:'DE06_076',10:'DE06_001'}
primary.update(replacements)
primary={k:('DE06_022' if v=='DE06_025' else v) for k,v in primary.items()}
# Every supplied generated reference/map/diagram shot is replaced by a verified graphic.
ref_graphics={3:'asia',5:'asia',11:'altai',16:'time',32:'coverage',47:'asia',51:'oceania',57:'plateau',59:'plateau',63:'plateau',77:'parentage',82:'asia',85:'asia',86:'taiwan',95:'new2026',99:'xujiayao'}
missing_fill={89:'DE06_081',105:'DE06_076'}
for cue,label in list(primary.items()):
 if label.startswith('DE06_'):
  cid=int(label[-3:])
  if cid in ref_graphics:primary[cue]='@'+ref_graphics[cid]
  elif label not in assets:primary[cue]=missing_fill[cid]
def seg(label,d=10,source=0,crop=1):return dict(label=label,duration=d,source_in=source,crop=crop)
plan=[]
for s in S:
 ch=next(int(c['chapter']) for c in C if int(c['start_seconds'])<=s['start_seconds']<int(c['end_seconds']))
 plan.append(dict(cue=s['id'],start=s['start_seconds'],end=s['end_seconds'],voice_en=s['voice_en'],chapter=ch,transition='cut',segments=[seg(primary[s['id']])],chapter_overlay='',lower_overlay=''))
# Twelve inspected shots in the existing thirty seconds, grouped by the three voice cues.
plan[0]['segments']=[seg('DE06_001',2,.2,1.14),seg('DE06_004',2,.5),seg('DE06_010',2.5,5),seg('DE06_001',3.5,.6,1.2)]
plan[1]['segments']=[seg('DE06_002',2.25,.5),seg('DE06_026',2.75,.6),seg('DE06_090',2.5,5),seg('DE06_044',2.5,4)]
plan[2]['segments']=[seg('DE06_020',2,5),seg('DE06_001',2,.3,1.12),seg('DE06_110',2,6),seg('@asia',4)]
pools={1:[2,10,14,20],2:[13,19,69,20],3:[22,24,26,27,29],4:[28,30,34,36,40],5:[43,46,49,52,54],6:[52,55,56,58],7:[44,62,66,68],8:[69,71,72,74,75,76],9:[78,79,80,83,84],10:[88,90,91,92,93,94],11:[96,97,98,100,101,102],12:[104,106,107,108,109,110]}
keep_full_graphics={6,7,16,31,34,36,45,46,47,49,62,64,68,71,79,81,87,89,93,98,101,103,106,111,124}
for p in plan[3:]:
 label=p['segments'][0]['label'];n=p['cue'];pool=pools[p['chapter']];other='DE06_'+f'{pool[n%len(pool)]:03d}'
 if label!=other and n not in keep_full_graphics and n not in [8,9]:p['segments']=[seg(label,6),seg(other,4,1,1.035 if n%2 else 1)]
# Short dissolves fit inside fixed ten-second slots; they do not shift the voice timeline.
for cue,a,b in [(12,'@altai','DE06_010'),(22,'DE06_013','DE06_024'),(44,'DE06_034','DE06_026'),(66,'DE06_060','DE06_062'),(76,'DE06_069','DE06_071'),(96,'DE06_091','DE06_081'),(116,'DE06_102','DE06_106'),(122,'DE06_110','@methods'),(126,'DE06_001','DE06_110')]:
 plan[cue-1].update(transition='dissolve',segments=[seg(a,5.25),seg(b,5.25,4.75 if not b.startswith('@') else 0)])
caption={1:'Illustrative bone replica; not the original Denisova fragment',2:'2010 / Molecular evidence reveals an unexpected human lineage',3:'DENISOVANS / A wider story across ancient Asia',8:'The specimen owner is not depicted',9:'Anonymous adults / Illustrative practical activity',15:'Recovered in 2008 / Discovery year differs from fossil age',19:'Generic objects / Context does not identify every maker',21:'Illustrative modern field documentation',27:'Laboratory imagery is illustration, not authentication',29:'Damaged-page analogy / Not a laboratory procedure',39:'Generic permanent-tooth teaching replica',50:'No verified face can be recovered from this image',58:'An inherited segment is not a certificate of cultural identity',65:'Genetic connection does not establish a personal journey',70:'Xiahe connection reported in 2019 / Generic jaw replicas',75:'Older collections can become informative through new methods',83:'Illustrative adult demonstration / Not original ancient footage',84:'Anonymous adult reconstruction / No identified ancient individuals',88:'Parentage inferred from a genome / No family portraits shown',97:'Penghu identification reported in 2025 / Generic adult-jaw replica',102:'A teaching collection is not a universal Denisovan portrait',108:'Illustrative anatomical models / Not the Bianfu specimens',117:'Illustrative adult craft demonstration',119:'Careful documentation and stewardship matter',121:'Return to the small surviving clue'}
for p in plan:
 n=p['cue'];ch=C[p['chapter']-1]
 if p['start']==int(ch['start_seconds']) and n>3 and not p['segments'][0]['label'].startswith('@'):
  im=Image.new('RGBA',(1280,720));d=ImageDraw.Draw(im);t=re.sub(r'in(202[56])',r'in \1',ch['title_en']).upper();size=23
  while d.textlength(t,font=ft(size,True))>1095:size-=1
  w=d.textlength(t,font=ft(size,True));d.rounded_rectangle((46,38,min(1234,w+95),124),radius=5,fill=(*bg,226));d.rectangle((46,38,51,124),fill=(*gold,255));d.text((70,49),f"{p['chapter']:02d} / DENISOVA",font=ft(11),fill=(*gold,255));d.text((70,77),t,font=ft(size,True),fill=(*fg,255));dest=R/'overlays'/f'chapter_{n:03d}.png';im.save(dest);p['chapter_overlay']='overlays/'+dest.name
 if n in caption:
  im=Image.new('RGBA',(1280,720));d=ImageDraw.Draw(im);t=caption[n];size=17
  while d.textlength(t,font=ft(size))>1125:size-=1
  w=d.textlength(t,font=ft(size));d.rounded_rectangle((46,605,82+w,659),radius=5,fill=(*bg,224));d.rectangle((46,605,51,659),fill=(*gold,255));d.text((65,623),t,font=ft(size),fill=(*fg,255));dest=R/'overlays'/f'lower_{n:03d}.png';im.save(dest);p['lower_overlay']='overlays/'+dest.name
 for a in p['segments']:
  assert (R/'graphics'/f"{a['label'][1:]}.png").exists() if a['label'].startswith('@') else a['label'] in assets
  assert a['source_in']+a['duration']<=10.0001 or a['label'].startswith('@')
 assert abs(sum(a['duration'] for a in p['segments'])-(10.5 if p['transition']=='dissolve' else 10))<.001
for n,head,sub,foot,hold in [(1,'ONE SMALL FRAGMENT','NO COMPLETE SKELETON','Illustrative bone replica',8.2),(2,'2010','A NEW HUMAN LINEAGE','Molecular evidence changes the comparison',7.2),(3,'DENISOVANS','A MUCH WIDER STORY','From a cave to questions across ancient Asia',5.5)]:
 im=Image.new('RGBA',(1280,720));d=ImageDraw.Draw(im);d.rounded_rectangle((46,498,980,662),radius=5,fill=(*bg,228));d.rectangle((46,498,52,662),fill=(*gold,255));d.text((71,513),head,font=ft(43,True),fill=(*fg,255));d.text((73,571),sub,font=ft(23,True),fill=(*gold,255));d.text((74,625),foot,font=ft(15),fill=(*muted,255));dest=R/'overlays'/f'lower_{n:03d}.png';im.save(dest);plan[n-1]['lower_overlay']='overlays/'+dest.name;plan[n-1]['lower_hold']=hold
(R/'EDIT_PLAN.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
with (R/'delivery/EDIT_TIMELINE.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['cue','start_seconds','end_seconds','transition','shot','source_label','source_in','duration','editor_crop','voice_en'])
 for p in plan:
  for k,a in enumerate(p['segments'],1):w.writerow([p['cue'],p['start'],p['end'],p['transition'],k,a['label'],a['source_in'],a['duration'],a['crop'],p['voice_en']])
summary=json.load(open(R/'INVENTORY_SUMMARY.json'));summary.update(topic=6,target_seconds=1260,opening_shots=sum(len(p['segments']) for p in plan[:3]),planned_shots=sum(len(p['segments']) for p in plan),graphic_count=len(list((R/'graphics').glob('*.png'))),used_source_clips=len({a['label'] for p in plan for a in p['segments'] if not a['label'].startswith('@')}),short_dissolves=sum(p['transition']=='dissolve' for p in plan),missing_context_solution={'59':'verified plateau map','82':'verified Asia map','86':'verified Taiwan Strait map','89':'inspected archive alternative DE06_081','99':'Xujiayao context graphic','105':'inspected mature adult demonstration DE06_076'},source_review='All104 clips sampled at0.8,4.9,9.1seconds; no claim of continuous manual viewing.',no_children_in_selected_visuals=True,rejected_source_labels=['DE06_025'],replaced_reference_prompt_ids=sorted(ref_graphics),english_reference_sha256='d733faf7cb437ff9db733a7f5f9f527aa177a3e688abdd270f313af2ab3605ad',audio='Existing English voice only; all source audio omitted; no music or SFX.',graphics='Modern Natural Earth geography and explicit explanatory schematics; not original fossils, measured Denisovan data, reconstructed faces or proven routes.')
assert all(a['label']!='DE06_025' for p in plan for a in p['segments'])
(R/'EDITOR_DECISIONS.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary),flush=True)
