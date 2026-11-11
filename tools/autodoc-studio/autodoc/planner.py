from __future__ import annotations
import math,re
from collections import Counter
import numpy as np
from .analysis import normalized

def time_windows(total_frames,fps,cues):
    """Partition integer frames exactly; opening time never extends narration."""
    if total_frames<=0:raise ValueError('Thời lượng không hợp lệ.')
    opening=min(total_frames,30*fps)
    count=min(10,max(1,opening//max(1,round(1.4*fps))))
    bounds=[round(i*opening/count) for i in range(count+1)]
    windows=[{'start_frame':a,'end_frame':b,'opening':True} for a,b in zip(bounds,bounds[1:])]
    cursor=opening
    ends=sorted({round(x['end']*fps) for x in cues})
    while cursor<total_frames:
        candidates=[x for x in ends if cursor+6*fps<=x<=min(total_frames,cursor+10*fps)]
        end=min(candidates,key=lambda x:abs(x-(cursor+8*fps))) if candidates else min(total_frames,cursor+8*fps)
        if 0<total_frames-end<2*fps:end=total_frames
        windows.append({'start_frame':cursor,'end_frame':end,'opening':False});cursor=end
    assert sum(w['end_frame']-w['start_frame'] for w in windows)==total_frames
    return windows

def words_for(cues,start,end):
    texts=[]
    for c in cues:
        if c['end']<=start or c['start']>=end:continue
        if c.get('words'):
            texts.extend(w['text'] for w in c['words'] if w['end']>start and w['start']<end)
        else:texts.append(c['text'])
    if not texts:
        closest=min(cues,key=lambda x:abs((x['start']+x['end'])/2-(start+end)/2));texts=[closest['text']]
    return ' '.join(texts).strip()

def make_plan(cues,files,candidates,features,screen_scores,model,duration,fps=24,screen_minors=True,screen_cards=False):
    total=math.ceil(duration*fps-1e-7);windows=time_windows(total,fps,cues)
    stop={'the','and','that','this','from','with','were','have','what','they','their','into','than','there','which','when','would','could','about','some','these','those','does','only','more','been','them','each','will','where','while','because','before','after','through','between','under','over','most','other','your','our','but','for','not','was','are','had','its','you','one','can','how','all','has','may','who','why','still'}
    counts=Counter(w.lower() for w in re.findall(r'[A-Za-z]{3,}',' '.join(x['text'] for x in cues)) if w.lower() not in stop)
    theme=', '.join(w for w,n in counts.most_common(7))
    queries=[]
    for w in windows:
        a,b=w['start_frame']/fps,w['end_frame']/fps
        local=words_for(cues,max(0,a-(8 if w['opening'] else 2)),min(duration,b+(8 if w['opening'] else 2)))
        queries.append(f'A documentary scene about {theme}. {local}')
    query_features=model.text(queries)
    minor_mask=(screen_scores[:,1]>.23)&((screen_scores[:,1]-screen_scores[:,0])>.045) if screen_minors else np.zeros(len(candidates),dtype=bool)
    card_mask=(screen_scores[:,2]>.24)&((screen_scores[:,2]-screen_scores[:,3])>.055) if screen_cards else np.zeros(len(candidates),dtype=bool)
    eligible=np.asarray([c['quality']>.012 for c in candidates])&~minor_mask&~card_mask
    if not eligible.any():raise ValueError('Không có cảnh phù hợp sau lọc hình. Bổ sung video cảnh vật/người trưởng thành rõ ràng, không bảng chữ.')
    source_count=Counter();recent=[];selected=[];plan=[];warnings=[]
    eligible_files={candidates[i]['file_id'] for i in np.flatnonzero(eligible)}
    for i,(w,q) in enumerate(zip(windows,query_features)):
        scores=features@q;base=scores.copy();available=eligible.copy()
        if w['opening']:
            unused=np.asarray([c['file_id'] not in source_count for c in candidates])&available
            if unused.any():available=unused
            else:
                unique=np.asarray([c['id'] not in selected for c in candidates])&available
                if unique.any():available=unique
        for j,c in enumerate(candidates):
            scores[j]-=min(.22,.055*math.sqrt(source_count[c['file_id']]))
            if c['file_id'] in recent[-3:]:scores[j]-=.11
            scores[j]+=.025*min(c['motion']/.04,1)+.01*min(c['quality']/.12,1)
        if selected:scores-=.035*(features@features[selected[-1]])
        needed=(w['end_frame']-w['start_frame'])/fps
        long_enough=np.asarray([c['source_duration']>=needed for c in candidates])&available
        if long_enough.any():available=long_enough
        scores[~available]=-np.inf;j=int(np.argmax(scores));c=candidates[j];f=files[c['file_id']]
        room=max(0,c['source_duration']-needed);offset=c['source_start']+room*.5
        looping=c['source_duration']+1e-4<needed
        # Loop only a real source video when footage is shorter. No tpad/frozen images.
        if looping:offset=c['source_start']
        crop=1+min(.055,.015*source_count[c['file_id']])
        item={**w,'index':i,'source_id':f['id'],'source_name':f['name'],'candidate_id':c['id'],'source_in':round(offset,4),'frames':w['end_frame']-w['start_frame'],'crop':round(crop,4),'semantic_score':round(float(base[j]),5),'text':words_for(cues,w['start_frame']/fps,w['end_frame']/fps),'transition':'cut','loop_source':looping}
        if not w['opening'] and i>0 and (sum(not x['opening'] for x in plan)+1)%5==0 and item['frames']>=fps:
            item['transition']='dissolve'
        plan.append(item);selected.append(j);recent.append(f['id']);source_count[f['id']]+=1
    opening_items=[x for x in plan if x['opening']]
    if len({x['source_id'] for x in opening_items})<len(opening_items):warnings.append('Không đủ nguồn khác nhau cho mọi cảnh mở đầu; đã chọn các đoạn/cỡ cắt khác nhau từ video có sẵn.')
    if any(x['loop_source'] for x in plan):warnings.append('Một số cảnh phải lặp video chuyển động vì nguồn ngắn; không dùng ảnh đứng để kéo dài.')
    low=[x['index']+1 for x in plan if x['semantic_score']<.19]
    if low:warnings.append(f'{len(low)} cảnh có điểm tương đồng thấp; nên xem lại các mốc được đánh dấu trong timeline.csv.')
    warnings.append('Khớp hình bằng AI tương đồng và lọc trẻ em/bảng chữ chỉ là ước lượng; cần xem bản dựng trước khi đăng.')
    return {'fps':fps,'total_frames':total,'voice_seconds':duration,'video_seconds':total/fps,'theme_keywords':theme,'opening_shots':len(opening_items),'opening_seconds':sum(x['frames'] for x in opening_items)/fps,'opening_distinct_files':len({x['source_id'] for x in opening_items}),'source_files':len(files),'screened_minor_windows':int(minor_mask.sum()),'screened_text_card_windows':int(card_mask.sum()),'warnings':warnings,'shots':plan}
