import hashlib,json,re,unicodedata,zipfile
from pathlib import Path
R=Path(__file__).parent;S=R/'voice/scripts';D=R/'documents'
chapters=json.loads((D/'LOCALIZATION_SOURCE_CHAPTERS.json').read_text())
profiles=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text())['profiles']
patches={
 'es-ES':[('pruebas de pruebas mecánicas del material','resultados de ensayos mecánicos del material'),('Mira el outlet','Observa el tubo de salida de agua'),('la lima','la cal')],
 'fr-FR':[('clastiques de chaux','fragments de chaux'),('gisement minéral','précipité minéral'),('le point de vente','le tube de sortie de l’eau'),('Il reliait des tas secs d\'ingrédients','Les chercheurs ont étudié des tas de matières sèches'),("L'enquête se poursuit.",'La recherche se poursuit.')],
 'ja-JP':[('食材','原料'),('ローマのレシピ','ローマの配合'),('鉱物石灰','石灰'),('白いインクルージョン','白い鉱物粒子'),('小さな内包物','小さな鉱物粒子'),('集水業者','集水容器'),('落下が起こり','水滴が落ち'),('失われた体力','失われた材料強度'),('放水管','排水チューブ'),('捜査は続いている。','探究は続きます。'),('実験では、石灰材料に由来する鉱物粒子を含む流れの減少が報告されましたが、対照標本は異なる挙動を示しました。','実験では、石灰由来の鉱物粒子を含む試料を通る水の流量が減少し、対照試料とは異なる挙動を示しました。')],
 'ko-KR':[('미네랄 석회','석회'),('광물 석회','석회'),('별도로 소석회합니다','별도로 물과 반응시켜 소석회로 만듭니다'),('이미 소석회된 석회','이미 소화된 석회'),('결의 주변','입자 주변'),('동일한 결의 중심','같은 입자의 중심부'),('단순히 물 공급이 중단된 집수 용기','단순히 물이 더 이상 모이지 않는 집수 용기'),('자료에 대해 어떤 이야기','재료에 대해 어떤 이야기'),('CE 79년','서기 79년'),('로마 요리법','로마 배합법'),('조사는 계속됩니다.','탐구는 계속됩니다.')],
 'de-DE':[('Minerallagerstätte','Mineralausfällung'),('Das reparierte Wort','Der Begriff repariert'),('Die Ermittlungen dauern an.','Die Forschung geht weiter.')],
 'it-IT':[('La parola familiare slaking','La parola idratazione'),('polimerizzazione','maturazione'),('polimerizzati','lasciati maturare'),('polimerizzato','lasciato maturare'),("L'indagine continua.",'La ricerca continua.')],
 'pt-PT':[('um procedimento em um truque','um procedimento num truque'),('em um truque','num truque'),('estágio de cura de fluxo contínuo','fase de preenchimento de fissuras com fluxo contínuo'),('evidências de testes mecânicos','resultados de ensaios mecânicos'),('fragmentos de cal misturados com material vulcânico seco','fragmentos de cal viva misturados com material vulcânico seco'),('79 d.C., interrompeu','79 d.C. interrompeu')],
 'nl-NL':[('nat en droog fietsen','herhaaldelijk natmaken en drogen'),('droge materiaalpalen','hopen droge grondstoffen'),('waardoor archeologen materiaal achterlieten van werk dat nog niet was voltooid','waardoor materiaal van onafgemaakte werkzaamheden voor archeologen bewaard bleef')],
 'pl-PL':[('Dochodzenie trwa.','Badania trwają.'),('obejrzyj outlet','obejrzyj rurkę odpływową')],
 'sv-SE':[('Watch the water discharge tube once more.','Titta på röret där vattnet rinner ut en gång till.'),('Utredningen fortsätter.','Undersökningen fortsätter.'),('våt och torr cykling','upprepad vätning och torkning'),('torra material pålar','högar med torra råmaterial')],
 'da-DK':[('Blød kalk','Brændt kalk'),('blød kalk','brændt kalk'),('våd og tør cykling','gentagen befugtning og tørring'),('Efterforskningen fortsætter.','Undersøgelsen fortsætter.')],
 'fi-FI':[('Tutkinta jatkuu.','Tutkimus jatkuu.'),('paranemisvaihe','halkeamien tiivistymisvaihe')],
 'nb-NO':[('Blekkkalk','Brent kalk'),('blekkkalk','brent kalk'),('våt og tørr sykling','gjentatt fukting og tørking'),('Etterforskningen fortsetter.','Undersøkelsen fortsetter.')],
 'cs-CZ':[('Vyšetřování pokračuje.','Výzkum pokračuje.'),('79 nl','79 našeho letopočtu')]
}
review=dict(topic_id='MOI-022',independent_native_review=False,independent_native_listening_review=False,
    source_adaptation='Full 13 English chapters retained in order; ambiguous material-science terms clarified for automated translation. Vietnamese independently rewritten by assistant with repeated transitions condensed.',
    assistant_review_scope='Full Vietnamese rewrite; all languages terminology/date and selected critical passage review, particularly chapters 4, 6, 7, 10 and closing; full-script five-word English leak scan; no independent native editorial or listening review.',
    rejected_initial_draft_issues=['outlet translated as electrical outlet or shop','wet/dry cycling translated as cycling a bicycle','dry material piles translated as stakes','mineral deposits translated as ore deposit','material strength translated as bodily strength','Japanese ingredients translated as food ingredients','Danish and Norwegian incorrect quicklime words'],locales={})
for p in profiles:
    locale=p['locale']
    if locale=='en-US':continue
    edits=[]
    if locale=='vi-VN':
        pieces=re.split(r'^## \d+\n',(R/'VI_NARRATION.txt').read_text(),flags=re.M)[1:];assert len(pieces)==13
        rows=[{**c,'locale':locale,'source_voice':c['voice'],'voice':body.strip(),'translation_method':'Assistant Vietnamese rewrite, terminology and scientific limits reviewed; no independent native listening review'} for c,body in zip(chapters,pieces)]
    else:
        rows=json.loads((S/f'{locale}.revision2-draft.json').read_text());assert len(rows)==13
        for row,c in zip(rows,chapters):
            assert row['source_voice']==c['voice']
            body=unicodedata.normalize('NFC',row['voice'])
            for old,new in patches[locale]:
                if old in body:body=body.replace(old,new);edits.append(dict(chapter=row['id'],old=old,new=new))
            row['voice']=body;row['translation_method']='Automated translation of clarified full chapters with assistant terminology, critical passage and closing edits; independent native review pending'
    out=S/f'{locale}.json';out.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    record=dict(locale=locale,chapters=13,assistant_full_rewrite=locale=='vi-VN',targeted_edits=edits,independent_native_review=False)
    review['locales'][locale]=record
    sha=hashlib.sha256(out.read_bytes()).hexdigest()
    (S/f'{locale}.context_checked').write_text(json.dumps(dict(script_sha256=sha,independent_native_review=False,review_scope=review['assistant_review_scope']),ensure_ascii=False,indent=2)+'\n')
    (D/f'{locale}.txt').write_text('\n\n'.join(x['voice'] for x in rows)+'\n',encoding='utf-8')
qa=dict(status='passed',topic_id='MOI-022',target_seconds=1282,voices=16,script_sha256={},english_leaks={},chapter_counts={},independent_native_review=False)
for p in profiles:
    locale=p['locale'];path=S/f'{locale}.json';rows=json.loads(path.read_text())
    assert len(rows)==(129 if locale=='en-US' else 13) and rows[0]['start']==0 and rows[-1]['end']==1282
    assert all(a['end']==b['start'] for a,b in zip(rows,rows[1:]))
    assert all(x['voice'].strip() and '\ufffd' not in x['voice'] for x in rows)
    leaks=[]
    if locale!='en-US':
        for row in rows:
            source=re.findall('[a-z]+',row['source_voice'].lower());target=' '.join(re.findall('[a-z]+',row['voice'].lower()))
            found={' '.join(source[i:i+5]) for i in range(len(source)-4) if ' '.join(source[i:i+5]) in target}
            if found:leaks.append(dict(chapter=row['id'],phrases=sorted(found)))
        assert not leaks,(locale,leaks)
        if locale!='vi-VN':assert '2023' in rows[0]['voice'] and '2025' in rows[9]['voice'] and '79' in rows[9]['voice']
    qa['script_sha256'][locale]=hashlib.sha256(path.read_bytes()).hexdigest();qa['english_leaks'][locale]=leaks;qa['chapter_counts'][locale]=len(rows)
for name,obj in [('VOICE_INPUT_QA.json',qa),('TRANSLATION_REVIEW.json',review),('LOCALIZATION_SOURCE_CHAPTERS.json',chapters)]:
    text=json.dumps(obj,ensure_ascii=False,indent=2)+'\n';(R/name).write_text(text,encoding='utf-8');(D/name).write_text(text,encoding='utf-8')
packet=R/'VOICE_INPUTS.zip'
with zipfile.ZipFile(packet,'w',zipfile.ZIP_DEFLATED) as z:
    for locale in [p['locale'] for p in profiles]:
        z.write(S/f'{locale}.json',f'voice/scripts/{locale}.json')
        if locale!='en-US':z.write(S/f'{locale}.context_checked',f'voice/scripts/{locale}.context_checked')
    for name in ['VOICE_INPUT_QA.json','TRANSLATION_REVIEW.json','LOCALIZATION_SOURCE_CHAPTERS.json']:z.write(R/name,name)
(R/'VOICE_INPUTS.sha256').write_text(hashlib.sha256(packet.read_bytes()).hexdigest()+'\n')
print(json.dumps(dict(status='passed',voices=16,packet_bytes=packet.stat().st_size,patches=sum(len(x['targeted_edits']) for x in review['locales'].values()),english_leaks=qa['english_leaks']),ensure_ascii=False),flush=True)
