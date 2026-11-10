import csv,hashlib,json,math,shutil,textwrap,re
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).parent;P=R.parent/'package'
for n in ['input','graphics','overlays','delivery','raw','scenes']:(R/n).mkdir(exist_ok=True)
source=json.loads((P/'SCENES_AND_PROMPTS.json').read_text());inventory=json.loads((R/'inventory.json').read_text());by={x['clip_id']:x for x in inventory}
voice=R.parent/'verified-release/BAISHIYA_08_My_Tieng_Anh.mp3';manifest=json.loads((R.parent/'verified-release/details/AUDIO_MANIFEST.json').read_text());en=next(x for x in manifest['voices'] if x['locale']=='en-US');assert hashlib.sha256(voice.read_bytes()).hexdigest()==en['sha256'];shutil.copy(voice,R/'input'/voice.name)
for src,dst in [(R.parent/'voice/scripts/en-US.json','en-US.json'),(R.parent/'verified-release/details/TIMING/en-US.srt','en-US.srt'),(P/'CHAPTERS_12.csv','CHAPTERS_12.csv')]:shutil.copy(src,R/'input'/dst)
F='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';FB='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def font(n,b=False):return ImageFont.truetype(FB if b else F,n)
BG='#0b1c27';INK='#f0eee5';GOLD='#e4b573';TEAL='#79b8bb';MUTE='#b4c3c7'
def nice(s):
 dois=re.findall(r'10\.\d{4,9}/[^\s]+',s)
 for i,v in enumerate(dois):s=s.replace(v,'DOI_CODE_'+chr(65+i))
 s=s.replace('EPAS1','EPAS_ONE_TOKEN')
 s=re.sub(r'([A-Za-z])(\d)',r'\1 \2',s)
 s=re.sub(r'(?<=[%])(?=[A-Za-z])',' ',s)
 s=re.sub(r'(?<=[,:;])(?=[A-Za-z])',' ',s)
 s=re.sub(r'(?<!\d),(?=\d)',' ,',s).replace(' ,',', ')
 s=s.replace('632,108','632, 108')
 s=s.replace('EPAS_ONE_TOKEN','EPAS1')
 for i,v in enumerate(dois):s=s.replace('DOI_CODE_'+chr(65+i),v)
 return s
def linewrap(d,s,f,maxw):
 words=s.split();out=[];line=''
 for w in words:
  test=(line+' '+w).strip()
  if line and d.textlength(test,font=f)>maxw:out.append(line);line=w
  else:line=test
 if line:out.append(line)
 return out
def card(name,kicker,title,lines,footer='Schematic explanation • no original specimen or measured genetic data'):
 kicker,title,lines,footer=nice(kicker),nice(title),[nice(x) for x in lines],nice(footer)
 im=Image.new('RGB',(1280,720),BG);d=ImageDraw.Draw(im);d.rectangle((0,0,14,720),fill=GOLD);d.text((62,54),kicker.upper(),font=font(19,True),fill=TEAL)
 y=113
 for t in linewrap(d,title,font(48,True),1150):d.text((60,y),t,font=font(48,True),fill=INK);y+=61
 y+=28
 for row in lines:
  d.ellipse((64,y+13,74,y+23),fill=GOLD)
  for t in linewrap(d,row,font(29),1080):d.text((96,y),t,font=font(29),fill=MUTE);y+=43
  y+=16
 d.line((60,642,1220,642),fill='#29444e',width=2);d.text((60,664),footer,font=font(16),fill=MUTE);im.save(R/'graphics'/f'{name}.png')
card('ALTITUDE','An invisible constraint','Same oxygen fraction. Lower pressure.',['Oxygen remains roughly21%of the air.','At altitude,lower air pressure means less oxygen per breath.','Walking and processing resources still require physical work.'],'Physiology explanation • schematic,not a measurement of an ancient individual')
card('AGE_MIN','The Xiahe mandible','At least ~160,000 years',['A uranium-series estimate from attached carbonate.','A minimum age,not an exact death date.','Ancient proteins supported a Denisovan connection in2019.'],'Chen et al.,2019 • DOI10.1038/s41586-019-1139-x')
card('COUNTS','A study published in2024','2,567 specimens examined',['1,857 specimens screened with ZooMS.','Morphology and molecular work were combined.','These are specimens and fragments—not a count of animals.'],'Xia et al.,2024 • Nature632,108–113 • CC BY4.0')
card('COLLAGEN','A molecular screening method','ZooMS: sorting the fragments',['Bone collagen can preserve informative peptide patterns.','A screening result guides the next investigation.','Detailed identification may require further analyses.'],'Collagen fingerprinting: schematic workflow,not a measured spectrum')
card('CAPRINES','The dominant faunal group','Caprines—especially bharal',['Bharal are often called blue sheep.','The assemblage is dominated by this broader animal group.','Presence and evidence of human processing are separate questions.'],'Xia et al.,2024 • Species names are evidence,not a reconstruction of a specific hunt')
card('MARKS','Reading physical traces','Cuts. Impacts. Alternative causes.',['Compare combinations of features and their context.','Carnivores,trampling and weathering can also modify bones.','One dramatic scratch is not a complete story.'],'Explanatory summary • no invented measured cut-mark statistics')
card('MARROW','Resources inside a hard shell','Marrow can contain substantial fat',['An outer bone wall protects material inside.','Fracture characteristics and impact marks inform interpretation.','The record does not supply a daily calorie budget.'],'Animal-resource explanation • generic teaching models only')
card('HIDES','Hides and reconstruction limits','A material is not an entire garment',['Processing traces can inform hide preparation.','Exact clothing designs and sewing methods remain unknown.','A convincing reconstruction is still an illustration.'],'Evidence limits retained • anonymous adult skill illustrations only')
card('TOOLS','More than food','Three expedient bone tools',['Available bone fragments could provide useful edges or shapes.','A possible equid-tooth retoucher was also reported.','Possible remains a tentative interpretation.'],'Xia et al.,2024 • These are explanatory statements,not drawings of the actual tools')
card('MOSAIC','A changing landscape','More than an empty frozen wilderness',['Open grassland. Shrub patches. Sheltered gullies.','Different habitats could offer different resources.','Not every species present is proven to have been hunted.'],'Ecological interpretation from the assemblage • not a surveyed ancient vegetation map')
card('LONG_TIME','A long archaeological sequence','Roughly190,000 to30,000 years ago',['The studied deposits span a long interval.','This does not establish continuous residence.','The identity of every visitor in every layer is not known.'],'Chronological framework • gaps and unequal preservation remain important')
card('FIRE','An unresolved question','Burned bones. Unresolved origin.',['Evidence of burning exists,but the available sample is limited.','Human activity and natural causes could not be resolved.','No specific ancient hearth is presented as a demonstrated fact.'],'Xia et al.,2024,Supplementary Information • limits retained in the narration')
card('RIB','Xiahe2','A Denisovan rib fragment',['Initial molecular screening prompted further investigation.','Detailed ancient-protein analysis supported identification.','Layer3 context:roughly48,000–32,000 years ago.'],'Xia et al.,2024 • Context age,not an exact date of death')
card('LIMIT','The meaning of an age estimate','Context dates are not a biography',['~48,000–32,000 years dates the layer containing Xiahe2.','It is not an exact birthday or death date.','It is not a date for the extinction of a lineage.'],'Dating distinction • no precise personal history inferred')
card('EVIDENCE','Different traces,different questions','Fossils. Sediment DNA. Worked bone.',['Fossils and molecules inform human presence and relationships.','Modified animal remains inform resource use.','The evidence has different strengths and limits.'],'Original explanatory synthesis • not a measured ancestry chart')
card('EPAS1','Evidence in living people','Modern Tibetan populations',['Research links the EPAS1 region with Denisovan-related ancestry.','The region is associated with aspects of high-altitude adaptation.','This does not recover the complete physiology of a Xiahe individual.'],'Huerta-Sanchez et al.,2014 • DOI10.1038/nature13408')
card('BODY_KNOWLEDGE','Biology meets practical life','Bodies. Knowledge. Resources.',['Living at altitude involves more than a single gene.','Useful materials still have to be obtained and processed.','The archaeological record preserves some of those actions.'],'Conceptual synthesis • no reconstructed ancient breathing measurements')
card('RECAP','The survival question','Food. Materials. Useful fragments.',['Animal processing provided access to different resources.','Bones preserve traces of decisions without a complete diary.','A cave offered shelter,not a guarantee.'],'Original narrative synthesis • illustrative visuals,not recovered personal biography')
# Properly spaced English labels,including compact numerals in authoring strings.
for p in (R/'graphics').glob('*.png'):pass
# Modern land geometry for geographical orientation; never an asserted migration route.
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
land=json.loads(Path('/workspace/work/beringia/edit/ne_110m_land.geojson').read_text());fig,ax=plt.subplots(figsize=(12.8,7.2),dpi=100);fig.patch.set_facecolor(BG);ax.set_facecolor(BG)
for feat in land['features']:
 g=feat['geometry']
 for poly in g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]:ax.add_patch(Polygon(poly[0],facecolor='#647d70',edgecolor='#aec2b0',linewidth=.6))
ax.set_xlim(50,150);ax.set_ylim(10,70);ax.set_axis_off();fig.subplots_adjust(0,0,1,1)
ax.text(100,56,'ASIA',color='#91a79b',fontsize=26,fontweight='bold')
for lon,lat,label,dx,dy in [(102.57,35.45,'BAISHIYA',1.4,-1.3),(84.68,51.40,'DENISOVA',1.4,1.3)]:ax.plot(lon,lat,'o',color=GOLD,markersize=8);ax.text(lon+dx,lat+dy,label,color=INK,fontfamily='DejaVu Sans',fontsize=15,fontweight='bold')
ax.text(54,65,'TWO SITES. A WIDER HUMAN HISTORY.',color=INK,fontsize=21,fontweight='bold');ax.text(54,13,'Modern geographic orientation • no migration route is asserted',color=MUTE,fontsize=11);fig.savefig(R/'graphics/MAP.png');plt.close(fig)
# Title and information overlays are authored in the editor,never generated as video text.
chapters=list(csv.DictReader(open(P/'CHAPTERS_12.csv',encoding='utf-8-sig')))
def overlay(name,tag,title,sub='',opening=False):
 tag,title,sub=nice(tag),nice(title),nice(sub)
 im=Image.new('RGBA',(1280,720),(0,0,0,0));d=ImageDraw.Draw(im)
 if opening and name!='opening.png':
  d.rounded_rectangle((38,46,1200,165),radius=10,fill=(6,20,29,224));d.text((61,61),tag,font=font(16,True),fill=GOLD);d.text((60,94),title,font=font(32,True),fill=INK)
 elif opening:
  d.rounded_rectangle((38,46,765,214),radius=12,fill=(6,20,29,218));d.text((61,63),tag,font=font(17,True),fill=GOLD);d.text((58,93),title,font=font(53,True),fill=INK);d.text((61,164),sub,font=font(22),fill=MUTE)
 else:
  d.rounded_rectangle((38,510,1218,664),radius=10,fill=(6,20,29,224));d.rectangle((38,510,46,664),fill=GOLD);d.text((66,523),tag,font=font(16,True),fill=TEAL);d.text((64,550),title,font=font(31,True),fill=INK)
  if sub:d.text((66,604),sub,font=font(18),fill=MUTE)
 im.save(R/'overlays'/name)
for c in chapters:overlay(f'chapter_{int(c["chapter"]):02d}.png',f'PART {int(c["chapter"]):02d} / BAISHIYA',c['title_en'],opening=True)
im=Image.open(R/'overlays/chapter_11.png').convert('RGBA');lower=Image.new('RGBA',im.size);lower.alpha_composite(im.crop((0,46,1280,166)),(0,450));lower.save(R/'overlays/chapter_11.png')
overlay('opening.png','THE SURVIVAL QUESTION','BAISHIYA','An ancient human story on a high plateau',True)
captions={5:('THE PLATEAU','~3,280 metres above sea level','Site elevation;illustrative landscape'),16:('MINIMUM AGE','At least ~160,000 years','Carbonate-crust estimate • Chen et al.,2019'),19:('ANCIENT PROTEINS','A Denisovan connection reported in2019','The molecular result does not supply a personal biography'),21:('CAVE SEDIMENTS','Denisovan mitochondrial DNA','Zhang et al.,2020 • separate from a recovered complete nuclear genome'),25:('THE2024 STUDY','2,567 faunal specimens examined','Specimens and fragments—not2,567 individual animals'),30:('COLLAGEN FINGERPRINTING','1,857 specimens screened with ZooMS','Morphology and molecular analysis were combined'),31:('DOMINANT FAUNAL GROUP','Caprines—especially bharal','Species interpretation • no particular hunt is reconstructed'),47:('SURFACE EVIDENCE','Compare traces and their context','Teaching models illustrate mechanisms,not original recovered specimens'),53:('RESOURCE USE','Meat. Marrow. Hides.','Xia et al.,2024'),58:('INSIDE THE BONE','Marrow can contain substantial fat','Generic clean teaching model'),72:('MATERIALS FOR MORE WORK','Three expedient bone tools','Simple shaping can still have practical value'),75:('KEEP THE QUALIFIER','A possible equid-tooth retoucher','Tentative interpretation,not a confirmed personal tool'),80:('A DIVERSE COLLECTION','Different animals. Different questions.','Not every species present is proven to have been hunted'),95:('OCCUPATION HISTORY','Repeated presence ≠ every winter','Seasonality and continuity require their own evidence'),104:('XIAHE2','A rib fragment identified as Denisovan','Detailed ancient-protein analysis • Xia et al.,2024'),105:('LAYER3 CONTEXT','~48,000–32,000 years ago','The layer’s age is not an exact date of death'),114:('MODERN TIBETAN POPULATIONS','EPAS1 and Denisovan-related ancestry','Not a complete recovered Xiahe genome'),125:('THE PRACTICAL RESPONSE','Food. Materials. Tools.','Parts of a survival story,not a complete diary')}
for cue,values in captions.items():overlay(f'fact_{cue:03d}.png',*values)
# Only the following visibly sampled source clips are excluded or restricted.
excluded={6:'Apparatus depiction is inconsistent;use a clear physiology schematic.',34:'Full spiral ram horns do not identify bharal.',41:'Highly engraved geometric marks risk being mistaken for ancient symbols.',48:'Prominent reconstructed skull is unnecessary and taxonomically ambiguous.',58:'Modern fenced pit does not illustrate the intended sediment-context point.',61:'Background figures have uncertain ages;omit whole clip.',78:'Strong geometric engravings could imply an unsupported symbol claim.',81:'Contains broadcaster-style logo;use unbranded inspected alternatives.',87:'Contains broadcaster-style logo and an unnecessary full skeleton.',93:'Stitched pouch could imply unestablished clothing/sewing details.',94:'Avoid prominent mixed skeletal displays when discussing the human rib.',99:'Animal skull does not illustrate the high-altitude body question.',100:'Generated display implies specific genetic results not shown by the research.',104:'Jaw imagery would confuse the distinction between fossils and modern genetic evidence.',108:'Mixed skull/table reconstruction adds no clear support to the narrated actions.',111:'Contains generated broadcaster-like subtitles;use clean cave alternatives.'}
# Cue-specific cut choices take precedence over file order.
choices={4:[4,3],5:[5,37],6:['@ALTITUDE',7],7:[103,31],8:[8,3],9:[40,43],10:[10,47],11:[11,15],12:[12,1],13:[13,16],14:[13,15],15:[15,19],16:[16,'@AGE_MIN'],17:['@AGE_MIN',13],18:[17,25],19:[18,13],20:['@MAP',4],21:[19,96],22:[13,20],23:[20,23],24:[24,110],25:[22,'@COUNTS'],26:[23,24],27:[24,57],28:[25,'@COLLAGEN'],29:[26,18],30:['@COUNTS',22],31:['@CAPRINES',28],32:[28,7],33:[70,73],34:[30,'@MOSAIC'],35:[40,45],36:[31,29],37:[32,33],38:[33,38],39:[32,31],40:[35,57],41:[36,23],42:[37,84],43:[38,69],44:[39,103],45:[31,79],46:[40,43],47:[40,115],48:[47,42],49:[43,53],50:[44,'@MARKS'],51:[45,77],52:[23,89],53:[20,112],54:[47,54],55:[40,43],56:[49,35],57:[50,59],58:[51,'@MARROW'],59:[51,56],60:[53,43],61:['@MARKS',53],62:[54,47],63:[55,54],64:[56,59],65:[57,112],66:[15,82],67:[59,51],68:[60,62],69:[62,112],70:[62,'@HIDES'],71:[109,'@HIDES'],72:[63,'@TOOLS'],73:[64,68],74:[65,63],75:[65,'@TOOLS'],76:[66,112],77:[67,119],78:[68,63],79:[69,29],80:[70,74],81:[69,113],82:[69,'@MOSAIC'],83:[73,23],84:[74,79],85:[83,'@MOSAIC'],86:[76,24],87:[77,89],88:[40,83],89:[79,80],90:[80,15],91:[15,'@LONG_TIME'],92:[82,'@LONG_TIME'],93:[83,20],94:[19,'@EVIDENCE'],95:[84,85],96:[85,'@FIRE'],97:['@FIRE',45],98:[85,82],99:[88,92],100:[89,91],101:[91,97],102:[91,17],103:[92,18],104:['@RIB',25],105:[15,'@RIB'],106:['@LIMIT',97],107:[96,89],108:[96,19],109:[3,98],110:[97,'@LIMIT'],111:[98,4],112:[37,103],113:['@EPAS1',105],114:[101,'@EPAS1'],115:[102,'@BODY_KNOWLEDGE'],116:[103,5],117:['@EVIDENCE',105],118:[105,17],119:[106,113],120:[107,35],121:[119,112],122:[109,'@BODY_KNOWLEDGE'],123:[110,24],124:[8,3],125:[112,'@RECAP'],126:[113,29],127:[114,15],128:[115,110],129:[13,19,91,'@EVIDENCE'],130:[117,40],131:[118,12],132:[40,9],133:[119,107],134:[120]}
hook=[(1,0),(5,.7),(70,.7),(8,.7),(20,.7),(40,.7),(54,.8),(18,.7),(4,.7),(109,.7),(91,.7),(120,0)]
crops={28:[0,200,720,405],32:[0,310,640,360]}
plan=[]
for row in source:
 cue=row['id'];selected=[a for a,b in hook[(cue-1)*4:cue*4]] if cue<=3 else choices[cue];durations=[2.5]*4 if len(selected)==4 else [10] if len(selected)==1 else [5,5]
 transition='cut'
 if cue in [13,25,36,47,58,69,80,91,102,113,124] and len(selected)==2 and not any(isinstance(x,str) and x.startswith('@') for x in selected):transition='dissolve';durations=[5.25,5.25]
 segments=[]
 for i,(label,dur) in enumerate(zip(selected,durations)):
  if isinstance(label,int):
   assert label in by and label not in excluded,(cue,label);name=f'BS08_{label:03d}';sin=hook[(cue-1)*4+i][1] if cue<=3 else 0 if dur==10 else round(.4+((cue+i)%4)*.65,2);assert sin+dur<=by[label]['seconds']+.01
   badge='TEACHING CAST' if label in [13,16] else 'TECHNIQUE ILLUSTRATION' if label in [9,35,39,42,47,49,52,54,55,60,64,67,107,109,119] else 'TEACHING MODEL' if label in [40,43,50,51,53,56,57,59,63,65,68,76,110,115,117] else 'ILLUSTRATIVE VISUALS'
  else:name=label;sin=0;badge='EXPLANATORY GRAPHIC'
  if cue==71 and i==0:sin=1.2
  segments.append(dict(label=name,source_in=sin,duration=dur,crop=1,crop_box=crops.get(label),badge=badge))
 c=next(x for x in chapters if int(x['start_seconds'])<=row['start_seconds']<int(x['end_seconds']));chapter_overlay='overlays/opening.png' if cue==1 else f'overlays/chapter_{int(c["chapter"]):02d}.png' if row['start_seconds']==int(c['start_seconds']) else None
 plan.append(dict(cue=cue,start_seconds=row['start_seconds'],end_seconds=row['end_seconds'],chapter=row['chapter'],voice_en=row['voice_en'],segments=segments,transition=transition,chapter_overlay=chapter_overlay,chapter_hold=4.4 if chapter_overlay and cue!=1 else 6.3,lower_overlay=f'overlays/fact_{cue:03d}.png' if cue in captions else None,lower_hold=7.7))
assert len(plan)==134 and sum(x['end_seconds']-x['start_seconds'] for x in plan)==1340 and sum(len(x['segments']) for x in plan[:3])==12
for x in plan:assert abs(sum(s['duration'] for s in x['segments'])-(.5 if x['transition']=='dissolve' else 0)-10)<.001
(R/'EDIT_PLAN.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
with (R/'delivery/EDIT_TIMELINE.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['cue','start_seconds','end_seconds','chapter','source_labels','transition','voice_en'])
 for x in plan:w.writerow([x['cue'],x['start_seconds'],x['end_seconds'],x['chapter'],';'.join(s['label'] for s in x['segments']),x['transition'],x['voice_en']])
source_manifest=dict(topic=8,clips=[dict(label=x['label'],source_name=x['original_name'],file_id=x['file_id'],bytes=x['original_bytes'],sha256=x['original_sha256'],source_audio=any(s['codec_type']=='audio' for s in x['streams']),upload_uri=x['original_uri']) for x in inventory],canonical_uploads_preserved=True,raw_source_publication=False)
(R/'SOURCE_MANIFEST.json').write_text(json.dumps(source_manifest,ensure_ascii=False,indent=2));decisions=dict(topic=8,seconds=1340,opening_shots=12,opening_seconds=30,english_voice_sha256=en['sha256'],english_words=3162,original_audio_tracks_excluded=35,no_music_or_SFX=True,source_review='114clips sampled at0.8s,midpoint,andend;not continuous manual viewing',exclusions={f'BS08_{k:03d}':v for k,v in excluded.items()},detail_only_crops={f'BS08_{k:03d}':v for k,v in crops.items()},crop_reason='Only body/hooves are used;full spiral-horn animals are not presented as verified bharal images.',missing_prompts=[2,14,27,72,75,116],missing_contexts_resolved_in_plan=True,no_children_in_selected_samples=True,scientific_limits=['Xiahejaw minimumage,not exactdeathdate','Xiahe2layercontext48–32ka,not exactdeathdate','Burningoriginsunresolved;noestablishedhearth','ModernTibetanEPAS1evidence,notrecoveredXiahegenome','Noassertedcontinuousoccupation','Noassertedmigrationroute'],render_source='Original upload bytes re-downloaded with checksums;analysis download caches only are evicted.',audio='Existing Englishreferenceonly;loudnessnormalizationwithoutretimingorpitchshift')
(R/'EDITOR_DECISIONS.json').write_text(json.dumps(decisions,ensure_ascii=False,indent=2));(R/'VISUAL_REVIEW_APPROVED.json').write_text(json.dumps(dict(status='passed',scope='Source-sample selection;final movie review still required',excluded_clips=list(decisions['exclusions']),no_children_in_selected_sampled_frames=True,not_continuous_manual_viewing=True),indent=2))
print(json.dumps(dict(cues=134,seconds=1340,shots=sum(len(x['segments']) for x in plan),opening_shots=12,used_clips=len({s['label'] for x in plan for s in x['segments'] if not s['label'].startswith('@')}),graphics=len(list((R/'graphics').glob('*.png'))),dissolves=sum(x['transition']=='dissolve' for x in plan))))
