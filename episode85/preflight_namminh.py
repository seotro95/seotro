import difflib,json
from render_common import R,S,PROFILES,normalized,accent,finish
from online_transport import request,configure,BACKENDS
locale='vi-VN';assert PROFILES[locale]['voice_id']=='vi-VN-NamMinhNeural';BACKENDS[locale]=configure(locale)
body='Một mảnh xương nhỏ trong hang Callao đã mở ra những câu hỏi lớn. Người Homo luzonensis là ai, và chúng ta có thể đặt họ ở đâu trên cây họ hàng?'
rows=[{'id':1,'start':0,'end':10,'voice':body}];S.mkdir(parents=True,exist_ok=True);(S/'vi-VN.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
out=R/'voice/vi_preview';out.mkdir(parents=True,exist_ok=True);p=out/'raw-001-01.wav';words=request(locale,body,p,'+0%')
coverage=difflib.SequenceMatcher(None,normalized(body),normalized(''.join(w['text'] for w in words)),autojunk=False).ratio();assert coverage>=.97
count=accent(p,words,locale);p.with_suffix('.meta.json').write_text(json.dumps({'coverage':coverage,'accents':count,'source_words':len(words)}))
j=finish(locale,rows,[[p]],out=out,target=10);assert j['decoded_frames_48000']==480000
qa={'status':'passed','voice_id':j['voice_id'],'gender':j['gender'],'locale':locale,'catalogue_verified':True,'decoded_frames_48000':480000,'sample_seconds':10,'sample_sha256':j['sha256'],'word_coverage_ratio':coverage,'native_adam_used':False,'source_commit':j['source_commit']}
(R/'NAM_MINH_PREFLIGHT_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2));print('ACTUAL_NAM_MINH_PREVIEW_VERIFIED',flush=True)
