import hashlib,json,re
from pathlib import Path
R=Path(__file__).parent;S=R/'voice/scripts'
fix={
 'ja-JP':[('テストされた巨大なサンプル','調査対象となったマンモスの標本群'),('自信を持って判定した','高い確度で判定した'),('コレクション','骨の集積'),('古い木片が若い火の中に入る','古い木片が後の時代の火で燃やされる')],
 'ko-KR':[('테스트된 거대한 샘플','조사한 매머드 표본 집단'),('자신있게 결정했습니다','높은 신뢰도로 판정했습니다'),('자신있게 밝힐 수 없는','확실하게 알 수 없는'),('컬렉션','동물 뼈의 집합'),('건축가의 활동','구조물을 만든 사람들의 활동'),('더 어린 불','후대에 피운 불')],
 'pt-PT':[('a amostra gigantesca testada','o conjunto de amostras de mamute analisadas'),('a amostra gigantesca','o conjunto de amostras de mamute'),('confiáveis','fiáveis'),('confiável','fiável'),('Dezessete','17'),('dezessete','17'),('Dezassete','17')],
 'es-ES':[('Diecisiete','17'),('diecisiete','17')],
 'fr-FR':[('Dix-sept','17'),('dix-sept','17')],
 'de-DE':[('Siebzehn','17'),('siebzehn','17')],
 'it-IT':[('Diciassette','17'),('diciassette','17')],
 'nl-NL':[('Zeventien','17'),('zeventien','17'),('zestig','60'),('Zestig','60'),('dertien','13')],
 'pl-PL':[('Siedemnaście','17'),('siedemnaście','17')],
 'sv-SE':[('Sjutton','17'),('sjutton','17')],
 'da-DK':[('Sytten','17'),('sytten','17')],
 'fi-FI':[('Seitsemäntoista','17'),('seitsemäntoista','17')],
 'nb-NO':[('Sytten','17'),('sytten','17')],
 'cs-CZ':[('Sedmnáct','17'),('sedmnáct','17')],
}
review=[]
for loc,changes in fix.items():
    p=S/f'{loc}.json';rows=json.loads(p.read_text())
    for row in rows:
        for a,b in changes:row['voice']=row['voice'].replace(a,b)
        row['editorial_status']='Chapter-context translation;assistant review of archaeological polysemy,critical figures,animal sex,tree-growth dating and regional terms;independent native editorial/listening review pending'
    p.write_text(json.dumps(rows,ensure_ascii=False,indent=2));p.with_suffix('.txt').write_text('\n\n'.join(x['voice'] for x in rows));p.with_suffix('.terminology-v2').write_text(hashlib.sha256(p.read_bytes()).hexdigest());p.with_suffix('.reviewed19').write_text('Assistant contextual/terminology review;independent native review pending')
    review.append(dict(locale=loc,chapters=12,source_ambiguities_clarified=['bone ring versus jewellery','animal killing versus human murder','occupation versus job','sediment versus financial deposit','tree growth layer versus bone circle','animal sex versus human gender','counts versus illustrations'],native_editorial_listening_review_pending=True))
(R/'TRANSLATION_REVIEW.json').write_text(json.dumps(dict(topic=19,reviewed_by='assistant',white_hmong_dialect_independently_verified=False,native_review_pending=True,notes='Vietnamese and Hmong separately edited;other locales translated with chapter context and targeted semantic repairs. Not a certification of native fluency.',locales=review),ensure_ascii=False,indent=2))
print('Fourteen regional scripts reviewed;Vietnamese and nativeHmong prepared separately.')
