import hashlib,json,re,time
from pathlib import Path
from prepare_scripts import LANGS,translate,adapt,source
R=Path(__file__).parent;S=R/'voice/scripts'
# Earlier translations used ambiguous English words; these are assistant editorial corrections.
fixes={
'es-ES':{'Marks apoyó actividades relacionadas con la carne, el tuétano y las pieles.':'Las marcas aportaban pruebas del procesamiento de carne, tuétano y pieles.','un manifestante adulto':'una persona adulta que demuestra una técnica','tres útiles instrumentos óseos':'tres herramientas de hueso elaboradas con una transformación mínima de fragmentos disponibles','Conveniente no significa que no tenga sentido.':'Una elaboración sencilla no implica falta de utilidad.','un posible retoque realizado a partir de un diente de équido':'una posible herramienta para retocar piedra, hecha con un diente de équido','Esa primera pantalla':'Esa primera prueba de cribado molecular','Survival deja':'La supervivencia deja'},
'fr-FR':{'Les calques peuvent contenir des espaces':'Les couches peuvent présenter des lacunes','Les gisements échantillonnés':'Les dépôts sédimentaires échantillonnés','Ce premier écran':'Ce premier test de criblage moléculaire','trois outils en os pratiques':'trois outils en os façonnés sommairement à partir de fragments disponibles','Expédient ne veut pas dire dénué de sens.':'Un façonnage simple ne signifie pas une absence d’utilité.','Survival laisse':'La survie laisse'},
'ja-JP':{'梅志屋':'白石崖洞窟','Baishiya':'白石崖洞窟','Xiahe2':'シャーハー二号','Xiahe':'シャーハー','ZooMS':'ズームズ法','EPAS1':'イー・ピー・エー・エス・ワン'},
'ko-KR':{'마크스':'이 흔적들','마크는':'이 흔적은','시위자':'기술을 시연하는 사람','첫 번째 화면':'첫 번째 분자 선별 검사','생존은 불균등한 기록을 남깁니다':'생존 활동은 불완전한 고고학 기록을 남깁니다'},
'pt-PT':{'pesquisadores':'investigadores','pesquisas':'investigações','equipe':'equipa','registro':'registo','contato':'contacto','confiável':'fiável','compartilhar':'partilhar','planejar':'planear','caverna':'gruta'},
}
original_sentences=[s.strip() for r in source for s in re.split(r'(?<=[.!?])\s+',r['voice']) if len(s.strip())>=20]
jp=dict((int(a),b) for a,b in (l.split('\t',1) for l in (R/'japanese_reviewed.tsv').read_text().splitlines()))
results=[]
for loc in LANGS:
 if loc in ['mww','vi-VN']:continue
 p=S/f'{loc}.json'
 # Wait only for the translator's final atomic-ready marker, not partial files.
 deadline=time.monotonic()+1800
 while not p.exists() or not p.with_suffix('.terminology-v2').exists():
  if time.monotonic()>deadline:raise TimeoutError(loc)
  time.sleep(3)
 rows=json.loads(p.read_text());repairs=[]
 for row in rows:
  before=row['voice'];out=jp[row['id']] if loc=='ja-JP' and row['id'] in jp else before
  for a,b in fixes.get(loc,{}).items():out=out.replace(a,b)
  en=row.get('source_en','');sentences=original_sentences+[s.strip() for s in re.split(r'(?<=[.!?])\s+',en) if len(s.strip())>=20]
  candidates=sorted(set(s for s in sentences if s in out),key=len,reverse=True)
  for sentence in candidates:
   if sentence not in out:continue
   time.sleep(6);translated=adapt(translate(sentence,LANGS[loc]),loc)
   if sentence in translated:raise ValueError((loc,row['id'],'provider repeatedEnglish',sentence))
   out=out.replace(sentence,translated);repairs.append(dict(chapter=row['id'],english=sentence,localized=translated))
  for a,b in fixes.get(loc,{}).items():out=out.replace(a,b)
  assert not any(s in out for s in sentences),(loc,row['id'],'English remains')
  if out!=before:row['translation_before_assistant_review']=before
  row['voice']=out;row['editorial_status']='Assistant scientific-context/terminology review and untranslated-sentence scan;independent native editorial/listening review pending'
 p.write_text(json.dumps(rows,ensure_ascii=False,indent=2));p.with_suffix('.txt').write_text('\n\n'.join(x['voice'] for x in rows));p.with_suffix('.terminology-v2').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'\n');p.with_suffix('.reviewed08').write_text('Scientific terminology/context and untranslated spans reviewed;native review pending\n')
 result=dict(locale=loc,chapters=len(rows),english_spans_repaired=repairs,manual_scientific_patches=loc in fixes,japanese_chapters_rewritten=[5,7,9,10] if loc=='ja-JP' else [],independent_native_review_pending=True);results.append(result);(R/'TRANSLATION_REVIEW.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print('REVIEW_READY',loc,'English repairs',len(repairs),flush=True)
print('All14nonmanual localized scripts reviewed',flush=True)
