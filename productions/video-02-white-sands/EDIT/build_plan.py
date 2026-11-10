import csv,json,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageEnhance
R=Path(__file__).parent
for folder in ['graphics','overlays','delivery','scenes']: (R/folder).mkdir(exist_ok=True)
assets={x['label']:x for x in json.loads((R/'inventory.json').read_text())}
script=json.load(open(R.parent/'package/SCENES_AND_PROMPTS.json'))
chap=list(csv.DictReader(open(R.parent/'package/CHAPTERS_12.csv')))
F='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; B='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def font(n,b=False):return ImageFont.truetype(B if b else F,n)
bg=(11,24,32);fg=(241,237,222);gold=(227,184,112);muted=(165,188,192);blue=(111,190,204)
def base(title,sub):
 im=Image.new('RGB',(1280,720),bg);d=ImageDraw.Draw(im);d.rectangle((48,48,54,127),fill=gold);d.text((75,43),title,font=font(32,True),fill=fg);d.text((77,96),sub,font=font(16),fill=muted)
 d.text((52,676),'WHITE SANDS  /  EXPLANATORY SCHEMATIC',font=font(12),fill=muted)
 return im,d
def save(im,name):im.save(R/'graphics'/f'{name}.png')
def photo(im,label,box):
 from PIL import ImageOps
 p=Image.open(assets[label]['frame']);im.paste(ImageOps.fit(p,(box[2]-box[0],box[3]-box[1])),box[:2])
def textlines(d,xy,lines,size=22,color=fg,gap=39):
 for i,t in enumerate(lines):d.text((xy[0],xy[1]+gap*i),t,font=font(size),fill=color)
# Modern coastline is traced from Natural Earth, with no invented migration arrows.
def mapim(name,title,sub,ice=False):
 im,d=base(title,sub);geo=json.load(open('/workspace/work/beringia/edit/ne_110m_land.geojson'))
 def xy(lon,lat):return (int(66+(lon+170)/120*850),int(625-(lat-5)/75*445))
 for f in geo['features']:
  g=f['geometry'];polys=[g['coordinates']] if g['type']=='Polygon' else g['coordinates']
  for p in polys:
   # Clip with a separate map canvas so distant continents do not paint the layout.
   pts=[xy(*v[:2]) for v in p[0]]
   d.polygon(pts,fill=(64,89,89),outline=(104,132,124))
 # Mask coordinates outside plot frame.
 d.rectangle((0,0,1280,159),fill=bg);d.rectangle((0,646,1280,719),fill=bg);d.rectangle((935,145,1280,655),fill=bg);d.rectangle((0,150,45,655),fill=bg)
 d.rectangle((48,48,54,127),fill=gold);d.text((75,43),title,font=font(32,True),fill=fg);d.text((77,96),sub,font=font(16),fill=muted)
 for lon,lat,t in [(-106.2,32.8,'WHITE SANDS'),(-150,63,'ALASKA')]:
  x,y=xy(lon,lat);d.ellipse((x-6,y-6,x+6,y+6),fill=gold);d.text((x+12,y-12),t,font=font(16,True),fill=fg)
 if ice:
  textlines(d,(950,200),['Ice sheets affected','inland access.','','An open passage','also needed usable','resources.','','No exact ice margin','or route is drawn.'],16,gap=33)
 else:textlines(d,(950,200),['Southern New Mexico','','Evidence of presence','far south of Alaska.','','Modern coastline;','ancient shorelines','were different.'],16,gap=34)
 d.text((52,676),'MODERN GEOGRAPHIC REFERENCE  /  NATURAL EARTH 1:110m',font=font(12),fill=muted);save(im,name)
mapim('map','A FOOTPRINT FAR SOUTH','White Sands, New Mexico  /  Geographic context')
mapim('ice','THE ROUTE QUESTION','Northern access and southern evidence are different questions',True)
# Layer sequence: deliberately no measured dimensions or fabricated actual section.
im,d=base('A STEP WITHIN A SEQUENCE','Schematic relationships, not a measured excavation profile')
for i,c in enumerate([(164,132,94),(131,112,90),(187,159,111),(113,105,91),(149,118,83)]):
 y=190+i*77;d.rectangle((80,y,785,y+76),fill=c)
 if i==2:
  d.line((80,y+3,785,y+3),fill=gold,width=5);d.ellipse((350,y-10,411,y+16),fill=bg)
textlines(d,(845,209),['Younger deposits','cover the surface.','','A footprint belongs','to its sedimentary','context.','','Older deposits lie','below the surface.'],21,gap=41)
save(im,'layers')
im,d=base('THE ORIGINAL AGE CLAIM','2021  /  Calibrated estimates, with uncertainty')
d.line((130,355,1130,355),fill=muted,width=3)
for x,t in [(245,'23,000'),(960,'21,000')]:d.line((x,340,x,370),fill=gold,width=4);d.text((x-74,392),t,font=font(32,True),fill=fg)
d.line((245,355,960,355),fill=gold,width=12);d.text((444,276),'YEARS AGO  /  APPROXIMATE',font=font(21),fill=gold)
textlines(d,(173,520),['Footprint-bearing layers were placed within this broad period.','This is not an exact birthday for every individual track.'],22,gap=41);save(im,'age')
im,d=base('THE OLD-CARBON PROBLEM','Why an aquatic plant can appear older than it is')
for x,title,lines in [(90,'ATMOSPHERE',['Carbon taken up by','terrestrial plants']), (690,'WATER',['Aquatic plants may also','take up older carbon'])]:
 d.rounded_rectangle((x,195,x+500,458),radius=14,fill=(25,45,53));d.text((x+28,228),title,font=font(25,True),fill=gold);textlines(d,(x+28,298),lines,23);d.text((x+28,397),'A DIFFERENT CARBON HISTORY',font=font(15),fill=muted)
textlines(d,(105,526),['Older starting carbon can bias a radiocarbon age.','Repeating the same biased sample type may repeat the same error.'],22,gap=42);save(im,'carbon')
im,d=base('TWO MATERIALS. ONE CARBON CLOCK.','Seeds and terrestrial pollen both use radiocarbon dating')
for x,title,lines in [(70,'AQUATIC SEEDS',['Possible reservoir effect','Carbon source matters']), (470,'TERRESTRIAL POLLEN',['Atmospheric carbon source','Tests the aquatic-carbon concern']), (870,'BURIED QUARTZ',['Luminescence signal','Different physical principle'])]:
 d.rounded_rectangle((x,208,x+345,484),radius=12,fill=(25,45,53));d.text((x+23,243),title,font=font(21,True),fill=gold);textlines(d,(x+23,329),lines,16,gap=40)
d.text((102,554),'Agreement is useful because the weaknesses differ.',font=font(26),fill=fg);save(im,'methods')
im,d=base('A MINERAL CLOCK','Optically stimulated luminescence  /  Conceptual mechanism')
for x,t,ls in [(75,'SUNLIGHT',['Sufficient light can','reset the signal.']), (480,'BURIAL',['Energy accumulates','from natural radiation.']), (885,'LABORATORY',['Stimulation releases','a measurable signal.'])]:
 d.rounded_rectangle((x,232,x+320,490),radius=14,fill=(25,45,53));d.ellipse((x+117,257,x+169,309),outline=gold,width=3);d.text((x+22,339),t,font=font(22,True),fill=gold);textlines(d,(x+22,395),ls,19,gap=34)
d.text((160,560),'The result estimates burial, with assumptions and uncertainty.',font=font(23),fill=fg);save(im,'quartz')
im,d=base('A WIDER GEOLOGICAL TEST','2025  /  The depositional record surrounding the tracks')
photo(im,'V273',(60,180,680,620));textlines(d,(730,205),['More than 23,600','to about 17,000 years ago','','This describes a broader','sedimentary record.','','It is not the age range','of every footprint.'],23,gap=44);save(im,'basin')
im,d=base('A REFINED FRAMEWORK','October 2026  /  Expanded footprint-bearing sequence')
photo(im,'V277',(60,180,665,620));textlines(d,(710,200),['20 stratigraphic horizons','','Approximately','23,500–21,700 years ago','','A refined sequence,','not a calendar day','for each step.'],23,gap=44);save(im,'refined')
im,d=base('WATER CHANGED. PEOPLE WERE PRESENT.','Lake Otero  /  Environmental interpretation')
photo(im,'V233',(60,190,625,509));photo(im,'V279',(655,190,1220,509))
d.text((80,529),'WET MARGINS',font=font(22,True),fill=gold);d.text((675,529),'A SHRINKING LAKE',font=font(22,True),fill=gold)
d.text((80,593),'Major drying episode: around 23,200 years ago  /  Approximate',font=font(21),fill=fg);save(im,'drying')
im,d=base('MOVEMENT IS NOT A COMPLETE BIOGRAPHY','A teaching diagram, not a traced archaeological trackway')
for x,y,ang in [(230,290,0),(335,405,0),(440,290,0),(545,405,0)]:
 d.ellipse((x,y,x+39,y+76),outline=gold,width=4)
 for k in range(5):d.ellipse((x-2+k*9,y-12,x+5+k*9,y-3),fill=gold)
textlines(d,(710,210),['Shape and spacing can','inform interpretations.','','Crossing tracks require','relative timing.','','A nearby animal print','does not prove a chase.'],23,gap=44);save(im,'tracks')
im,d=base('PRESENCE IS A MINIMUM CONSTRAINT','An old footprint is evidence that people were already there')
photo(im,'V225',(60,190,670,610));textlines(d,(722,209),['People present by then.','','Not the first arrival date.','','Not a proven journey.','','Routes need other','independent evidence.'],25,gap=46);save(im,'presence')
im,d=base('ONE ARROW CANNOT TELL THE WHOLE STORY','Possible movements must fit timing, geography and usable resources')
photo(im,'V295',(60,190,680,610));textlines(d,(727,208),['Coastal possibilities','','Inland possibilities','','Different groups and times','','White Sands alone','does not select a route.'],22,gap=46);save(im,'routes')
im,d=base('WHAT REMAINS OPEN','Better evidence can refine an explanation')
photo(im,'V276',(65,185,685,620));textlines(d,(740,208),['ROUTES','','LOCAL ENVIRONMENTS','','DATING DETAILS','','RELATIONSHIPS BETWEEN','DIFFERENT RECORDS'],22,gap=43);save(im,'questions')
im,d=base('THE CHAIN OF EVIDENCE','Each connection must survive alternative explanations')
for x,t,ls in [(62,'STEP',['A body acts on','suitable ground.']), (367,'BURIAL',['Later deposits','protect the trace.']), (672,'CONTEXT',['Layers connect','samples to events.']), (977,'TESTS',['Dating methods','check the age.'])]:
 d.rounded_rectangle((x,235,x+245,498),radius=12,fill=(25,45,53));d.text((x+23,272),t,font=font(26,True),fill=gold);textlines(d,(x+23,359),ls,19,gap=36)
save(im,'chain')
# Mapping selected by contact-sheet review, rather than file numbering.
labels={1:'M001',2:'V225',3:'V226',4:'@map',5:'V224',6:'V229',7:'V230',8:'M008',9:'@quartz',10:'M021',11:'M011',12:'V233',13:'V234',14:'V235',15:'V236',16:'V237',17:'V238',18:'V239',19:'V240',20:'V243',21:'@layers',22:'@layers',23:'V243',24:'V244',25:'V245',26:'V246',27:'V247',28:'V248',29:'@age',30:'V249',31:'V250',32:'@layers',33:'V251',34:'V252',35:'V253',36:'V254',37:'@carbon',38:'V256',39:'@carbon',40:'@carbon',41:'V259',42:'M042',43:'V260',44:'V261',45:'V262',46:'V263',47:'V264',48:'@methods',49:'V270',50:'@quartz',51:'V268',52:'M052',53:'V269',54:'V270',55:'V271',56:'@basin',57:'V273',58:'V274',59:'V275',60:'V276',61:'V277',62:'@refined',63:'@refined',64:'V279',65:'V280',66:'V281',67:'V238',68:'V234',69:'V284',70:'V285',71:'V286',72:'M072',73:'@tracks',74:'@tracks',75:'V289',76:'V281',77:'@map',78:'@presence',79:'V293',80:'@ice',81:'V295',82:'@routes',83:'V293',84:'V297',85:'V298',86:'V299',87:'V300',88:'V301',89:'V303',90:'V303',91:'@questions',92:'V230',93:'V305',94:'@chain',95:'V259',96:'@methods',97:'@presence',98:'V226',99:'@questions',100:'V312'}
def seg(label,duration=10,source_in=0,crop=1):return dict(label=label,duration=duration,source_in=source_in,crop=crop)
plan=[]
for i,s in enumerate(script,1):plan.append(dict(cue=i,start=(i-1)*10,end=i*10,voice_en=s['voice_en'],transition='cut',segments=[seg(labels[s['clip_id']])],chapter=(i-1)//11+1,chapter_overlay='',lower_overlay=''))
# Eight purposeful shots, aligned to the first three unchanged narration cues.
plan[0]['segments']=[seg('M001',6,0),seg('V225',4,1)]
plan[1]['segments']=[seg('V224',3,1),seg('V254',4,1),seg('M008',3,2)]
plan[2]['segments']=[seg('V234',4,0),seg('V235',3,1),seg('V228',3,3)]
# Sustained diagrams stay readable; other scenes use changes in scale and evidence cutaways.
cutaways={5:'V243',6:'V260',7:'V259',8:'V254',10:'V233',11:'M008',13:'V226',14:'V238',16:'V233',17:'V238',19:'V254',20:'V233',21:'V246',22:'V226',23:'V298',24:'@layers',25:'@layers',26:'V254',27:'V243',28:'V254',29:'V246',30:'V245',31:'@layers',32:'V251',33:'V250',34:'V249',36:'V246',37:'M042',38:'V251',39:'V248',40:'V240',41:'V259',42:'V252',43:'V243',44:'V250',45:'V250',46:'V256',47:'V233',48:'M042',49:'V250',50:'V259',51:'M042',52:'@methods',53:'V259',54:'V263',55:'V260',56:'V262',57:'V264',58:'V263',59:'@methods',60:'V262',61:'V268',62:'V270',63:'V268',64:'@methods',65:'V268',66:'@methods',67:'V275',68:'V273',69:'V271',71:'V273',72:'V277',73:'V273',74:'V275',75:'V246',76:'V259',77:'V277',78:'@refined',81:'V273',82:'@drying',83:'V279',84:'V237',85:'V279',86:'V289',87:'V234',88:'V233',89:'M072',90:'V286',91:'M072',92:'V243',93:'V284',94:'V254',95:'V235',96:'V286',97:'V305',98:'V237',99:'V254',102:'V293',105:'V295',107:'V234',109:'V243',110:'V228',111:'V299',112:'V298',113:'V243',114:'V244',115:'V301',116:'V303',117:'V301',118:'V300',120:'V248',121:'M072',122:'V289',123:'@chain',124:'V259',125:'V250',126:'@methods',128:'V234',129:'V235',130:'V233',131:'V312',132:'V225'}
for cue,other in cutaways.items():
 if cue%2==0 or cue in {5,7,13,17,23,27,33,37,43,51,57,61,67,73,83,89,95,99,105,111,115,121,125,129,131}:
  label=plan[cue-1]['segments'][0]['label']
  if label!=other:plan[cue-1]['segments']=[seg(label,6),seg(other,4,2 if not other.startswith('@') else 0)]
# Keep refined track chronology and lake drying ages visually distinct.
plan[77]['segments']=[seg('V277',6),seg('V246',4,2)]
plan[79]['segments']=[seg('V276',6),seg('V273',4,2)]
plan[84]['segments']=[seg('@drying',6),seg('V279',4,2)]
# Dissolves only for environmental shifts and the closing callback.
for cue,a,b in [(20,'V239','V233'),(81,'V233','V279'),(129,'V226','V233'),(131,'V312','V225')]:
 plan[cue-1]['transition']='dissolve';plan[cue-1]['segments']=[seg(a,5.3),seg(b,5.3,4.7)]
# Reject inaccurate generated maps, clocks, giant scientific objects and misleading track models.
rejected=['V242','V227','V257','V258','V265','V267','V272','V287','V288','V291','V292','V294','V296','V302','V309','V311','M032','M082']
for p in plan:
 for s in p['segments']:
  assert s['label'] not in rejected,s
  assert s['label'].startswith('@') or s['label'] in assets
 assert abs(sum(s['duration'] for s in p['segments'])-(10.6 if p['transition']=='dissolve' else 10))<.001
 cue=p['cue'];im=Image.new('RGBA',(1280,720));d=ImageDraw.Draw(im);drawn=False
 if cue==2:
  d.rounded_rectangle((48,484,615,630),radius=4,fill=(*bg,216));d.rectangle((48,484,53,630),fill=(*gold,255));d.text((73,505),'WHITE SANDS',font=font(38,True),fill=(*fg,255));d.text((76,564),'THE FOOTPRINTS AND THE CLOCKS',font=font(19),fill=(*gold,255));drawn=True
 elif cue%11==1 and cue>1:
  n=p['chapter']-1;title=chap[n]['title_en'].upper();tw=d.textlength(title,font=font(21,True));d.rounded_rectangle((48,38,min(1232,94+tw),117),radius=4,fill=(*bg,217));d.rectangle((48,38,53,117),fill=(*gold,255));d.text((70,49),f'{n+1:02d} / WHITE SANDS',font=font(11),fill=(*gold,255));d.text((70,75),title,font=font(21,True),fill=(*fg,255));drawn=True
 if drawn and not p['segments'][0]['label'].startswith('@'):
  path=R/'overlays'/f'{cue:03d}.png';im.save(path);p['chapter_overlay']=str(path)
 captions={15:'ANCIENT LAKE OTERO  /  ILLUSTRATIVE RECONSTRUCTION',28:'Separate layers can represent separate visits',42:'White Sands entered an existing scientific debate',58:'2023  /  Terrestrial pollen supported the earlier age framework',64:'2023  /  Quartz luminescence supplied an independent physical test',68:'2025  /  A broader geological investigation',84:'Daily life shown here is illustrative; individual biographies are unknown',93:'A small print does not identify a particular child or family',105:'HYPOTHETICAL COASTAL SETTING  /  NOT A PROVEN ROUTE',115:'Protected fossil tracks are not a general visitor walking attraction',116:'Museum scenes are illustrative; no community identity is assigned',132:'An ordinary journey. An extraordinary surviving record.'}
 if cue in captions:
  im=Image.new('RGBA',(1280,720));d=ImageDraw.Draw(im);t=captions[cue];f=font(17 if len(t)<90 else 15);tw=d.textlength(t,font=f);d.rounded_rectangle((48,609,82+tw,659),radius=4,fill=(*bg,216));d.rectangle((48,609,52,659),fill=(*gold,255));d.text((65,625),t,font=f,fill=(*fg,255));path=R/'overlays'/f'lower_{cue:03d}.png';im.save(path);p['lower_overlay']=str(path)
(R/'EDIT_PLAN.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
with (R/'delivery/EDIT_TIMELINE.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['cue','start_seconds','end_seconds','transition','shot','source_label','source_file','source_in','duration','voice_en'])
 for p in plan:
  for n,s in enumerate(p['segments'],1):w.writerow([p['cue'],p['start'],p['end'],p['transition'],n,s['label'],str(R/'graphics'/f"{s['label'][1:]}.png") if s['label'].startswith('@') else assets[s['label']]['name'],s['source_in'],s['duration'],p['voice_en']])
(R/'EDITOR_DECISIONS.json').write_text(json.dumps({'uploaded_unique_clips':len(assets),'rejected_generated_maps_or_misleading_visuals':rejected,'reason':'Inaccurate geography, invented charts, inconsistent intended scene, implausible representations, or distracting generated labels; use inspected alternatives and explicit explanatory schematics.','opening_shots':8,'english_reference_sha256':'0746d9175c956ff15e27121945fc15438c93c20456a3bc4ee711af273f4b3a06','audio':'Original English narration only; all source clip audio excluded.'},indent=2))
print('Built',len(plan),'cues;',sum(len(p['segments']) for p in plan),'shots;',len(list((R/'graphics').glob('*.png'))),'graphics')
