import json,re
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'documents';S=R/'voice/scripts'
chapters=json.loads((D/'CHAPTERS_13.json').read_text())
def save(locale,texts,method):
    assert len(texts)==13
    rows=[dict(c,voice=t,source_voice=c['voice'],translation_method=method) for c,t in zip(chapters,texts)]
    (S/f'{locale}.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    (D/f'{locale}.txt').write_text('\n\n'.join(texts)+'\n')
    def ts(t):return f'{t//3600:02}:{t%3600//60:02}:{t%60:02},000'
    (D/f'{locale}.srt').write_text('\n\n'.join(f'{r["id"]}\n{ts(r["start"])} --> {ts(r["end"])}\n{r["voice"]}' for r in rows)+'\n')
if __name__=='__main__':
    vi=re.split(r'\n\s*\n',(R/'vi-reviewed.txt').read_text().strip())
    save('vi-VN',vi,'Assistant rewritten Vietnamese from English; independent native listening review pending')
    report=[]
    for p in S.glob('*.json'):
        rows=json.loads(p.read_text());locale=p.stem
        if locale=='en-US':continue
        assert len(rows)==13 and rows[0]['start']==0 and rows[-1]['end']==1242
        joined=' '.join(r['voice'] for r in rows)
        assert all(r['voice'].strip() for r in rows)
        dates={year:bool(re.search(year,joined)) for year in ['1991','2001','2022','2023','2025','2026']}
        report.append(dict(locale=locale,chapters=len(rows),nonempty=True,dates_in_numerals=dates,word_count=len(joined.split()),independent_native_review=False))
    (D/'TRANSLATION_REVIEW.json').write_text(json.dumps(dict(method='Automated country-language drafts with explicit numeric years, assistant contextual/terminology checks; vi and mww rewritten separately. No independent native editorial or listening certification.',locales=report),ensure_ascii=False,indent=2))
    print('vi chapter word counts',[len(t.split()) for t in vi])
