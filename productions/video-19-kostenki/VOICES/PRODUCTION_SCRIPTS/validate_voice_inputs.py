import hashlib,json,re
from pathlib import Path
R=Path(__file__).parent;S=R/'voice/scripts'
profiles=json.loads((R/'BASELINE_VOICE_PROFILES.json').read_text());ids={p['locale']:p for p in profiles['profiles']}
assert len(ids)==17 and sum(p['gender']=='Male' for p in ids.values())==16 and ids['mww']['voice_id']=='hmong-female-3'
required={1:[11,25000],3:[12,60],5:[2025],6:[2025,39,30,17,13],8:[2020],9:[18000]}
review=[]
bad={'ja-JP':['預金','職業','指輪','殺人','木の成長した骨'],'ko-KR':['예금','직업','반지','살인'],'vi-VN':['giết người','tiền gửi','chiếc nhẫn','17 con là nữ','xương hình tròn của cây']}
for loc in ids:
    p=S/f'{loc}.json';rows=json.loads(p.read_text());assert len(rows)==(122 if loc=='en-US' else 12)
    assert rows[0]['start']==0 and rows[-1]['end']==1215
    if loc=='en-US':
        assert sum(len(x['voice'].split()) for x in rows)==2816
        assert all(x['id']==i+1 and x['start']==i*10 and x['end']==min((i+1)*10,1215) for i,x in enumerate(rows))
    else:
        assert p.with_suffix('.terminology-v2').read_text().strip()==hashlib.sha256(p.read_bytes()).hexdigest(),loc
        assert p.with_suffix('.reviewed19').exists(),loc
        for i,row in enumerate(rows):
            assert row['id']==i+1 and row['start']==i*100 and row['end']==((i+1)*100 if i<11 else 1215)
            assert row['voice'].strip() and not re.search(r'\b(\w+)(?:\s+\1){4,}\b',row['voice'],re.I)
            for term in bad.get(loc,[]):assert term not in row['voice'],(loc,i+1,term)
            t=re.sub(r'[.,\s\u00a0\u202f]','',row['voice'])
            for n in required.get(i+1,[]):assert str(n) in t,(loc,i+1,n)
    review.append(dict(locale=loc,cues=len(rows),seconds=1215,input_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),critical_values_preserved=True,voice_id=ids[loc]['voice_id'],gender=ids[loc]['gender']))
(R/'VOICE_INPUT_QA.json').write_text(json.dumps(dict(status='passed',voices=17,english_words=2816,english_cues=122,english_last_cue_seconds=5,seconds=1215,frames_48k=58320000,translated_chapter_seconds=[100]*11+[115],profiles_preserved=True,native_editorial_listening_review_pending=True,locales=review),ensure_ascii=False,indent=2))
print('All17input scripts,critical figures,IDs and timing boundaries validated.')
