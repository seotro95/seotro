import csv,json,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
R=Path(__file__).parent
for name in ['graphics','overlays','delivery','scenes','review']:(R/name).mkdir(exist_ok=True)
a={x['label']:x for x in json.loads((R/'inventory.json').read_text())}
script=json.load(open(R.parent/'package/SCENES_AND_PROMPTS.json'))
chap=list(csv.DictReader(open(R.parent/'package/CHAPTERS_12.csv')))
F='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';B='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def ft(n,b=False):return ImageFont.truetype(B if b else F,n)
bg=(10,24,32);fg=(242,238,224);gold=(226,182,111);muted=(162,187,193);teal=(111,190,199)
def base(title,sub):
 im=Image.new('RGB',(1280,720),bg);d=ImageDraw.Draw(im);d.rectangle((48,44,54,124),fill=gold);d.text((75,40),title,font=ft(31,True),fill=fg);d.text((77,94),sub,font=ft(16),fill=muted);d.text((52,676),'MAL\'TA  /  EXPLANATORY SCHEMATIC  /  NOT MEASURED GENOMIC DATA',font=ft(12),fill=muted);return im,d
def lines(d,xy,ls,size=22,gap=40,col=fg):
 for n,t in enumerate(ls):d.text((xy[0],xy[1]+n*gap),t,font=ft(size),fill=col)
def write_image(im,path):
 if path.exists():
  old=Image.open(path)
  if old.mode==im.mode and old.size==im.size and old.tobytes()==im.tobytes():return
 im.save(path)
def save(im,name):write_image(im,R/'graphics'/f'{name}.png')
def photo(im,label,box):im.paste(ImageOps.fit(Image.open(a[label]['frame']), (box[2]-box[0],box[3]-box[1])),box[:2])
def dashed(d,pts,fill=gold,width=3,on=11,off=8):
 for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
  length=math.hypot(x2-x1,y2-y1)
  for st in range(0,int(length),on+off):
   en=min(length,st+on);d.line((x1+(x2-x1)*st/length,y1+(y2-y1)*st/length,x1+(x2-x1)*en/length,y1+(y2-y1)*en/length),fill=fill,width=width)
# Locked reference images were rendered from Natural Earth modern land/lake geometry.
def region(name,title,sub,ref,bounds,marks,relation=False):
 im,d=base(title,sub);box=(55,168,1225,621);im.paste(Image.open(R.parent/'package/REFERENCES'/ref).resize((1170,453)),box[:2]);d=ImageDraw.Draw(im)
 def xy(lon,lat):
  if lon<0:lon+=360
  return (55+(lon-bounds[0])/(bounds[1]-bounds[0])*1170,621-(lat-bounds[2])/(bounds[3]-bounds[2])*453)
 for lon,lat,t in marks:
  x,y=xy(lon,lat);d.ellipse((x-5,y-5,x+5,y+5),fill=gold);w=d.textlength(t,font=ft(17,True));tx=max(65,min(x+12,1212-w));ty=max(175,min(y-24,591));d.rectangle((tx-5,ty-3,tx+w+5,ty+23),fill=bg);d.text((tx,ty),t,font=ft(17,True),fill=fg)
 if relation:
  x1,y1=xy(103.5,52.85);x2,y2=xy(250,49);dashed(d,[(x1+5,y1+32),(x2-15,y2+30)],teal,3)
  d.rounded_rectangle((667,508,1182,598),radius=7,fill=bg);lines(d,(687,525),['Shared ancestry, not a demonstrated journey.','MA-1 is a sampled relative, not a route.'],18,31)
 d.rectangle((0,651,1280,720),fill=bg);d.text((52,676),'MODERN GEOGRAPHIC ORIENTATION  /  NATURAL EARTH 1:110m  /  APPROXIMATE SITE REGIONS',font=ft(12),fill=muted);save(im,name)
region('pacific_fixed','A RELATIONSHIP ACROSS CONTINENTS','MA-1-related populations and part of Indigenous American ancestry','NORTH_PACIFIC_MODERN_BASE.png',(45,285,20,82),[(103.5,52.85,"MAL'TA"),(211,63,'ALASKA'),(250,49,'NORTH AMERICA')],True)
region('baikal_fixed',"MAL'TA, SIBERIA",'West of Lake Baikal  /  This is the archaeological site, not the Mediterranean island','BAIKAL_MODERN_BASE.png',(95,120,45,62),[(103.5,52.85,"MAL'TA"),(108,54,'LAKE BAIKAL'),(106.5,50.35,'UST-KYAHTA REGION')])
region('yana_fixed','A WIDER SIBERIAN RECORD','Yana and Mal\'ta were separated by geography and thousands of years','YANA_MODERN_BASE.png',(95,180,48,80),[(103.5,52.85,"MAL'TA  /  ~24,000 YEARS"),(135.4,70.7,'YANA  /  ~31,600 YEARS')])
im,d=base('BERINGIA: GEOGRAPHIC CONTEXT','A broad former land connection, rather than a narrow bridge')
p=Image.open(R.parent/'package/REFERENCES/NPS_BERINGIA_BATHYMETRY_REFERENCE.png').convert('RGB');p=ImageOps.contain(p,(1190,450));im.paste(p,((1280-p.width)//2,163))
d.text((59,628),'NPS reference: approximately 21,000 BP. Not an exact 24,000-year coastline or MA-1 travel route.',font=ft(16),fill=fg);d.rectangle((0,663,1280,720),fill=bg);d.text((52,680),'SOURCE: U.S. NATIONAL PARK SERVICE  /  ORIGINAL SOURCE LABELS RETAINED',font=ft(12),fill=muted);save(im,'beringia')
im,d=base('RELATED DOES NOT MEAN DIRECT ANCESTOR','A genetic relationship does not identify a personal journey')
photo(im,'V342',(58,185,681,616));lines(d,(730,216),['A distant relative can','reveal a missing branch.','','MA-1 did not personally','found another population.','','Relatedness is not','a travel itinerary.'],23,43);save(im,'related')
im,d=base('DAMAGED, MIXED, INCOMPLETE','Recovering ancient DNA requires more than finding a fragment')
for row in range(5):
 y=205+row*65
 for k in range(6):
  x=80+k*91+(row%2)*25;length=47+(k%3)*10;d.rounded_rectangle((x,y,x+length,y+16),radius=5,fill=teal);d.rectangle((x,y,x+7,y+16),fill=gold)
lines(d,(780,207),['Short surviving fragments','','Damage at fragment ends','','Possible modern contamination','','Controls and comparisons','help test authenticity.'],20,43)
d.text((83,581),'Colours are explanatory; a colour does not establish a molecule\'s age.',font=ft(19),fill=fg);save(im,'damage')
im,d=base('TWO PUBLICATION DATES. ONE ANCIENT LIFE.','Separate research history from the age of the child')
for x,title,ls in [(72,'~24,000 YEARS AGO',["The child's lifetime",'Approximate age']), (482,'20 NOVEMBER 2013',['Paper published online','Raghavan and colleagues']), (892,'2 JANUARY 2014',['Nature issue date','The same research'])]:
 d.rounded_rectangle((x,228,x+315,488),radius=10,fill=(25,44,51));d.text((x+20,266),title,font=ft(20,True),fill=gold);lines(d,(x+20,352),ls,18,37)
save(im,'publication')
im,d=base('INHERITANCE ACROSS GENERATIONS','A simplified teaching model, not an actual family genome')
for row,(y,t) in enumerate([(220,'ONE PARENT'),(360,'OTHER PARENT')]):
 d.text((88,y),t,font=ft(19,True),fill=gold)
 for k in range(10):d.rounded_rectangle((343+k*67,y-1,394+k*67,y+35),radius=6,fill=teal if (k+row)%3 else gold)
d.text((89,511),'DESCENDANT',font=ft(19,True),fill=gold)
for k in range(10):d.rounded_rectangle((343+k*67,510,394+k*67,546),radius=6,fill=teal if k%2 else gold)
d.text((343,588),'Recombination reshuffles inherited material.',font=ft(22),fill=fg);save(im,'inheritance')
im,d=base('ONE LINE IS ONLY PART OF THE PICTURE','Maternal and paternal lineages versus variation across the autosomes')
for x,t,ls in [(65,'MITOCHONDRIAL DNA',['Usually passed from mothers','One maternal line']), (473,'Y CHROMOSOME',['A narrow paternal line','in many male individuals']), (881,'AUTOSOMES',['Numbered chromosomes','Many ancestral relationships'])]:
 d.rounded_rectangle((x,222,x+333,510),radius=12,fill=(25,44,51));d.text((x+20,258),t,font=ft(19,True),fill=gold);lines(d,(x+20,352),ls,17,39)
d.text((123,572),'A single inherited lineage is not the entire family network.',font=ft(24),fill=fg);save(im,'lineages')
im,d=base('PATTERNS ACROSS MANY POSITIONS','Illustrative sequence blocks, not actual MA-1 genomic data')
for row in range(3):
 y=240+row*105;d.text((76,y+10),f'COMPARISON {row+1}',font=ft(17),fill=fg)
 for k in range(16):d.rectangle((300+k*52,y,340+k*52,y+45),fill=[teal,gold,(151,160,161)][(k//3+(row if k%5==0 else 0))%3])
d.text((107,589),'Repeated sharing patterns are tested against alternative relationships.',font=ft(22),fill=fg);save(im,'variants')
im,d=base('FROM A TREE TO A NETWORK','A simplified relationship model, with no measured ancestry proportions')
for xy,t in [((260,250),['MA-1-related northern','Eurasian populations']),((950,250),['Ancient East Asian-','related populations']),((640,505),['Ancestral histories connected to','Indigenous peoples of the Americas'])]:
 x,y=xy;d.ellipse((x-22,y-22,x+22,y+22),fill=gold if y==505 else teal)
 for n,s in enumerate(t):d.text((x-d.textlength(s,font=ft(20,True))/2,y+42+n*29),s,font=ft(20,True),fill=fg)
dashed(d,[(278,270),(620,485)],teal,4);dashed(d,[(930,270),(660,485)],teal,4)
d.text((132,167),'Populations are related; the child is a sampled individual within a larger history.',font=ft(20),fill=fg);save(im,'network')
im,d=base('WHAT DOES A LINE MEAN?','Always distinguish movement from genetic relatedness')
for y,t,sub,style in [(237,'DEMONSTRATED JOURNEY','Needs independent route evidence.','solid'),(361,'POSSIBLE CONNECTION','A hypothesis to investigate.','dash'),(485,'GENETIC RELATIONSHIP','Shared inheritance; not an itinerary.','dot')]:
 if style=='solid':d.line((90,y,340,y),fill=gold,width=4)
 else:dashed(d,[(90,y),(340,y)],teal,4,13 if style=='dash' else 3,9)
 d.text((400,y-22),t,font=ft(23,True),fill=fg);d.text((400,y+18),sub,font=ft(19),fill=muted)
save(im,'connections')
im,d=base('A MODEL IS NOT A UNIVERSAL PIE CHART','Estimates depend on samples, comparisons and historical models')
photo(im,'V360',(62,187,679,614));lines(d,(725,211),['No single proportion applies','to every community.','','DNA, language and craft','measure different histories.','','A genetic category is not','a modern nationality.'],21,43);save(im,'model_limits')
im,d=base('TWO DIFFERENT KINDS OF TIME','A population-divergence estimate is not the date of one journey')
d.rounded_rectangle((85,232,1195,355),radius=11,fill=(25,44,51));d.text((110,249),'POPULATION HISTORY',font=ft(22,True),fill=gold);d.rectangle((560,292,1080,320),fill=teal);d.text((111,299),'An estimated interval',font=ft(20),fill=fg)
d.rounded_rectangle((85,424,1195,547),radius=11,fill=(25,44,51));d.text((110,441),'A DATED ARCHAEOLOGICAL EVENT',font=ft(22,True),fill=gold);d.ellipse((805,475,831,501),fill=gold);d.text((111,491),'A separate observation',font=ft(20),fill=fg);save(im,'event_time')
im,d=base('SEPARATED BY THOUSANDS OF YEARS','Approximate individual ages, not one household or an unbroken lineage')
d.line((118,349,1162,349),fill=muted,width=3)
for age,title,sub in [(31600,'YANA','~31,600 years ago'),(24000,"MAL'TA",'~24,000 years ago'),(14000,'UST-KYAHTA-3','~14,000 years ago')]:
 x=150+(33000-age)/(33000-12000)*980;d.ellipse((x-8,341,x+8,357),fill=gold);d.text((x-66,261),title,font=ft(22,True),fill=fg);d.text((x-80,397),sub,font=ft(20),fill=fg)
d.text((130,542),'Older',font=ft(19),fill=muted);d.text((1053,542),'Younger',font=ft(19),fill=muted);save(im,'timeline')
im,d=base('A RECONSTRUCTION IS NOT A PORTRAIT','The people shown illustrate possibilities, not verified likenesses')
photo(im,'V327',(62,187,680,617));lines(d,(737,212),['His personal name','','The language he heard','','A verified facial likeness','','These are not recovered','from the evidence here.'],22,43);save(im,'unknown_person')
im,d=base('ONE SAMPLE IS ONE VIEW','New evidence can reveal connections and expose a model\'s limits')
photo(im,'V393',(62,187,681,617));lines(d,(732,208),['Compare independent samples.','','Test alternative models.','','Keep missing evidence visible.','','Related genomes need not','represent identical populations.'],21,43);save(im,'comparison')
# Original filename numbering is only a locator; selections follow visual review.
labels={};normal=313
for cid in range(1,101):
 if cid%10==2:labels[cid]=f'M{cid:03d}'
 else:labels[cid]=f'V{normal}';normal+=1
labels.update({1:'V402',6:'@pacific_fixed',11:'@baikal_fixed',21:'@damage',24:'@damage',26:'@damage',27:'V330',30:'@inheritance',33:'@lineages',35:'@variants',38:'@pacific_fixed',39:'@pacific_fixed',40:'@publication',43:'@model_limits',45:'@network',46:'@pacific_fixed',48:'@connections',50:'@network',51:'@comparison',52:'V354',58:'@network',60:'@model_limits',61:'@model_limits',65:'@beringia',71:'@event_time',73:'@yana_fixed',74:'@network',76:'@network',77:'@baikal_fixed',78:'@timeline',88:'V315',89:'@unknown_person',91:'V313',93:'@comparison',98:'@variants'})
def seg(label,duration=10,source_in=0,crop=1):return dict(label=label,duration=duration,source_in=source_in,crop=crop)
plan=[]
for i,s in enumerate(script,1):plan.append(dict(cue=i,start=(i-1)*10,end=i*10,voice_en=s['voice_en'],transition='cut',segments=[seg(labels[s['clip_id']])],chapter=(i-1)//10+1,chapter_overlay='',lower_overlay=''))
# Eight shots in the existing first 30 seconds; no added intro runtime.
plan[0]['segments']=[seg('V402',4,0),seg('V385',3,1),seg('V315',3,1)]
plan[1]['segments']=[seg('M002',4,0),seg('V328',3,1),seg('V330',3,1)]
plan[2]['segments']=[seg('V314',5,0),seg('@pacific_fixed',5)]
cutaways={4:'V327',5:'@network',6:'V315',7:'@related',8:'M042',9:'V362',10:'V324',12:'M012',13:'V371',14:'V325',15:'V324',16:'V337',17:'V398',18:'V329',19:'M082',20:'V314',21:'V332',22:'V345',23:'V334',24:'V332',25:'V314',26:'V334',27:'M042',28:'V334',29:'@publication',30:'@variants',31:'V340',32:'@inheritance',33:'@lineages',34:'@lineages',35:'V342',36:'@lineages',37:'V344',38:'@variants',39:'V359',40:'@variants',41:'V319',42:'V338',44:'@related',45:'V342',46:'M072',47:'V327',48:'V351',49:'@network',51:'V342',52:'@connections',53:'V356',54:'V363',55:'M042',56:'V360',57:'V359',58:'@comparison',59:'V361',60:'V342',61:'V318',62:'@network',63:'V363',64:'V365',65:'V359',66:'@model_limits',67:'V368',68:'V385',69:'V330',70:'@pacific_fixed',72:'V371',73:'V356',74:'V373',75:'V371',76:'V315',77:'V375',78:'@event_time',79:'@connections',80:'V330',81:'@timeline',82:'@network',83:'V393',84:'@baikal_fixed',85:'V338',86:'@baikal_fixed',87:'@timeline',88:'V360',89:'V319',90:'M012',91:'M082',92:'M082',93:'V329',94:'V385',95:'V324',96:'V328',97:'V384',98:'V314',99:'V369',100:'V402',101:'V327',102:'@network',103:'V398',104:'@unknown_person',105:'M042',106:'V402',107:'M092',108:'V383',109:'V396',110:'@network',111:'V313',112:'V385',113:'V398',114:'V330',115:'V315',116:'@related',117:'@comparison',118:'@connections',119:'V325'}
for cue,other in cutaways.items():
 if cue%2==0 or cue in {5,7,13,17,21,25,29,33,37,41,45,51,55,61,67,73,77,81,85,89,93,97,101,105,111,115,117,119}:
  src=plan[cue-1]['segments'][0]['label']
  if src!=other:plan[cue-1]['segments']=[seg(src,6),seg(other,4,2 if not other.startswith('@') else 0)]
plan[33]['segments']=[seg('@lineages',6),seg('V342',4,2)]
# Replace a generated bone of the wrong anatomical type with generic archive context.
plan[26]['segments']=[seg('V330',5),seg('M042',5)]
# Avoid consecutive identical map panels during the central result.
plan[40]['segments']=[seg('@pacific_fixed',6),seg('V319',4,2)]
plan[41]['segments']=[seg('V338',4,2),seg('@network',6)]
# Gentle dissolves mark a change of scale/time, rather than every cut.
for cue,x,y in [(10,'V315','V321'),(20,'V328','V314'),(70,'V369','V371'),(112,'V397','V385'),(120,'V401','V402')]:
 plan[cue-1]['transition']='dissolve';plan[cue-1]['segments']=[seg(x,5.3),seg(y,5.3,4.7)]
rejected=['V341','V317','V322','V331','V333','V335','V336','V339','V343','V346','V347','V348','V350','V352','V353','V355','V357','V358','V364','V366','V367','V370','V376','V377','V378','V380','V381','V382','V391','V392','V394','V395','V400','M052']
for p in plan:
 for s in p['segments']:
  assert s['label'] not in rejected,s
  assert s['label'].startswith('@') or s['label'] in a
 assert abs(sum(s['duration'] for s in p['segments'])-(10.6 if p['transition']=='dissolve' else 10))<.001
 cue=p['cue'];im=Image.new('RGBA',(1280,720));d=ImageDraw.Draw(im);drawn=False
 if cue==2:
  d.rounded_rectangle((48,484,657,630),radius=4,fill=(*bg,216));d.rectangle((48,484,53,630),fill=(*gold,255));d.text((74,503),"MAL'TA",font=ft(40,True),fill=(*fg,255));d.text((76,566),'THE CHILD AND A MISSING ANCESTRY',font=ft(19),fill=(*gold,255));drawn=True
 elif cue%10==1 and cue>1:
  n=p['chapter']-1;t=chap[n]['title_en'].upper();w=d.textlength(t,font=ft(21,True));d.rounded_rectangle((48,38,min(1232,94+w),117),radius=4,fill=(*bg,217));d.rectangle((48,38,53,117),fill=(*gold,255));d.text((70,49),f"{n+1:02d} / MAL'TA",font=ft(11),fill=(*gold,255));d.text((70,75),t,font=ft(21,True),fill=(*fg,255));drawn=True
 if drawn and not p['segments'][0]['label'].startswith('@'):
  out=R/'overlays'/f'{cue:03d}.png';write_image(im,out);p['chapter_overlay']=str(out)
 captions={4:'ABOUT 24,000 YEARS AGO  /  ANONYMOUS RECONSTRUCTION',10:'Reconstructed daily life, not a verified portrait or biography',16:'Excavations began in 1928  /  Illustrative field scene',17:'Commonly discussed age: about 3–4 years  /  Approximate',18:'REPLICA OBJECTS  /  Meanings remain debated',27:'MA-1 was sampled from an upper arm bone  /  Archive imagery is illustrative',28:'MA-1 is a research identifier; his personal name is unknown',30:'Sequence graphics are explanatory, not actual MA-1 genomic data',33:'Mitochondrial DNA traces one maternal line, not all ancestry',34:'A paternal lineage is one narrow part of a larger network',44:'RELATED POPULATIONS  /  NOT A DIRECT ANCESTOR CLAIM',48:'Genetic relatedness does not assign identity, nationality or sovereignty',56:'Shared-pattern analogy  /  Not a biological mechanism',63:'Simplified relationship model  /  No universal ancestry percentage',64:'Ancient populations are not two modern nations',67:'Genetic ancestry, language and craft can follow different histories',73:'Illustrative journey  /  Not the route of MA-1',75:'Movements and contacts over many generations',81:'2019 study  /  Yana individuals: approximately 31,600 years old',84:'2020 study  /  Tooth model is illustrative, not the Ust-Kyahta specimen',85:'Ust-Kyahta-3 individual: approximately 14,000 years old',94:'ILLUSTRATIVE LEARNING SCENE  /  Unknown individuals and relationships',104:'A cinematic reconstruction is not a verified likeness',105:'Consultation scene is illustrative, not a documented research meeting',119:'People, practical skills and care behind the population history'}
 if cue in captions:
  im=Image.new('RGBA',(1280,720));d=ImageDraw.Draw(im);t=captions[cue];f=ft(17 if len(t)<90 else 15);w=d.textlength(t,font=f);d.rounded_rectangle((48,609,82+w,659),radius=4,fill=(*bg,216));d.rectangle((48,609,52,659),fill=(*gold,255));d.text((65,625),t,font=f,fill=(*fg,255));out=R/'overlays'/f'lower_{cue:03d}.png';write_image(im,out);p['lower_overlay']=str(out)
(R/'EDIT_PLAN.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
with (R/'delivery/EDIT_TIMELINE.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['cue','start_seconds','end_seconds','transition','shot','source_label','source_file','source_in','duration','voice_en'])
 for p in plan:
  for n,s in enumerate(p['segments'],1):w.writerow([p['cue'],p['start'],p['end'],p['transition'],n,s['label'],str(R/'graphics'/f"{s['label'][1:]}.png") if s['label'].startswith('@') else a[s['label']]['name'],s['source_in'],s['duration'],p['voice_en']])
(R/'EDITOR_DECISIONS.json').write_text(json.dumps({'uploaded_unique_clips':100,'source_clips_containing_audio':30,'rejected_source_labels':rejected,'reason':'Wrong generated geography, invented readable scientific plots, misleading anatomical model, inappropriate symbolic object, or mismatch with intended scene. Use inspected alternatives and labelled explanatory graphics.','opening_shots':8,'english_reference_sha256':'60d7bb588b483a57c543c16173d4006e1728d347f6e26fc284ada48d75394136','audio':'Existing expressive English narration only; original clip audio entirely excluded; no music or SFX.','source_selection':'Visual review of every uploaded clip via contact sheets; original embedded scene numbers do not determine timeline position.'},indent=2))
print('Built',len(plan),'cues;',sum(len(p['segments']) for p in plan),'shots;',len(list((R/'graphics').glob('*.png'))),'graphics;',len({s['label'] for p in plan for s in p['segments'] if not s['label'].startswith('@')}),'source clips')
