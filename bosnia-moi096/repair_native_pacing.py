"""Repair only out-of-range cue pacing with the same native voice and words."""
import hashlib,json,math,shutil
from render_common import PROFILES,seconds,normalized,digest,accent
from online_transport import request

def repair(locale,rows,raws,out):
    audit=[];repaired=[];result=[]
    for row,paths in zip(rows,raws):
        duration=row['end']-row['start'];pause=.12 if duration>2 else .08
        before=sum(seconds(p) for p in paths)/(duration-pause)
        audit.append(dict(id=row['id'],tempo_before=before,needs_repair=not .55<=before<=1.65))
        if .55<=before<=1.65:
            result.append(paths);continue
        assert locale=='en-US' and len(paths)==1,'Use a reviewed locale-specific repair for localized chapters'
        base=.02;target=1.55 if before>1.65 else .70
        rate_percent=math.ceil(((1+base)*before/target-1)*100)
        assert -25<=rate_percent<=35,('Native pacing change needs review',row['id'],rate_percent)
        rate=f'{rate_percent:+d}%';source=out/f'raw-{row["id"]:03}-native-{rate_percent:+d}.wav'
        words=request(locale,row['voice'],source,rate,attempts=4)
        assert normalized(''.join(w['text'] for w in words))==normalized(row['voice'])
        after=seconds(source)/(duration-pause)
        assert .55<=after<=1.65,('Native repair still outside pacing range',row['id'],after)
        dest=out/f'raw-{row["id"]:03}-paced.wav';shutil.copyfile(source,dest)
        accents=accent(dest,words,locale)
        meta=dict(request_signature=hashlib.sha256((row['voice']+'\0'+PROFILES[locale]['voice_id']+'\0'+rate).encode()).hexdigest(),voice_id=PROFILES[locale]['voice_id'],rate=rate,coverage=1.0,accents=accents,source_words=len(words),native_pacing_repair=True,source_native_sha256=digest(source),source_original_raw_sha256=digest(paths[0]),tempo_before=before,tempo_after=after)
        dest.with_suffix('.meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
        repaired.append(dict(id=row['id'],rate=rate,tempo_before=before,tempo_after=after,voice_id=PROFILES[locale]['voice_id'],words_preserved=True))
        result.append([dest]);print('NATIVE_PACING_REPAIRED',locale,row['id'],rate,before,after,flush=True)
    report=dict(status='passed',locale=locale,thresholds_unchanged=[.55,1.65],cues_checked=len(rows),repaired=repaired,audit=audit)
    (out/'native_pacing_repair.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return result,report
