import hashlib,json
from pathlib import Path
R=Path(__file__).parent;S=R/'voice/scripts';repairs=[]
ko=dict((int(a),b.replace('주엠에스','줌스법')) for a,b in (l.split('\t',1) for l in (R/'korean_reviewed.tsv').read_text().splitlines()))
patches={'ja-JP':{3:{'支配的なグループはヤギ、特に青い羊と呼ばれるバラルでした。':'最も多いのはヤギやヒツジを含む分類群、特にブルーシープとも呼ばれるバーラルでした。','岩の多い国':'岩の多い土地','1 つのボディ':'一つの個体','1 つの部分は識別に抵抗する可能性があります。':'一片だけでは識別できない場合もあります。'},4:{'洞窟の動物の破片':'洞窟の動物の骨片'},8:{'他の遺跡':'他の動物の遺存体','文書化された処理は、大型の草食動物の写真だけを超えて広がりました。':'確認された加工は、大型草食動物だけに限られませんでした。'}},'ko-KR':{9:{'동굴의 퇴적물 퇴적물':'동굴의 퇴적물','서열의 일부':'퇴적 기록의 일부','바로 화재입니다':'바로 불입니다'}}}
for loc in ['ja-JP','ko-KR']:
 p=S/f'{loc}.json';before=p.read_bytes();rows=json.loads(before);changes=[]
 for row in rows:
  old=row['voice'];n=row['id']
  if loc=='ja-JP' and n==11:row['voice']=(R/'japanese_chapter11_reviewed.txt').read_text().strip()
  if loc=='ko-KR' and n in ko:row['voice']=ko[n]
  for a,b in patches.get(loc,{}).get(n,{}).items():row['voice']=row['voice'].replace(a,b)
  if row['voice']!=old:
   row['translation_before_second_scientific_review']=old;row['editorial_status']='Assistant reviewed scientific meanings and locally readable phrasing;independent native editorial/listening review pending';changes.append(n)
 p.write_text(json.dumps(rows,ensure_ascii=False,indent=2));p.with_suffix('.txt').write_text('\n\n'.join(x['voice'] for x in rows));p.with_suffix('.terminology-v2').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'\n')
 repairs.append(dict(locale=loc,chapters_changed=changes,input_before_sha256=hashlib.sha256(before).hexdigest(),input_after_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),reason='Scientific translation review:caprine taxonomy,stonecuttingedge,equidtooth,screeningmeaning,altitudebiologynotpolitics;regenerateonlyaffectedlocale,retainothers',wording_en_unchanged=True));print(loc,'changed chapters',changes,'chars',[(x['id'],len(x['voice'])) for x in rows if x['id'] in changes])
(R/'LOCALIZATION_REPAIRS.json').write_text(json.dumps(repairs,ensure_ascii=False,indent=2))
