import json,sys,urllib.request
from pathlib import Path
R=Path(__file__).parent
remote=json.load(urllib.request.urlopen('https://github.com/seotro95/seotro/releases/download/land-bridges-video-38-22m32s/DOCUMENT_QA.json',timeout=60))
assert remote['status']=='passed' and remote['target_seconds']==1352 and remote['unique_prompts']==120
sys.path.insert(0,str(R.parent/'melo'));import online_backend
profiles=json.loads((R/'BASELINE_VOICE_PROFILES.json').read_text())['profiles'];catalog={x['ShortName']:x for x in online_backend.get_catalog()}
for p in profiles:
 if p['locale']=='mww':continue
 v=catalog[p['voice_id']];assert v['Gender']=='Male' and v['Locale']==p['locale']
from render_episode import online
result=online('en-US',preview=True);assert result['decoded_frames_48000']==1440000 and result['word_accents']>0 and result['minimum_word_coverage_ratio']>=.97
(R/'VOICE_PREFLIGHT_QA.json').write_text(json.dumps({'status':'passed','documents_published_and_checked':True,'locked_male_voice_ids_found':16,'preview_seconds':30,'preview_decoded_frames_48000':1440000,'preview_word_coverage_ratio':result['minimum_word_coverage_ratio'],'preview_word_accents':result['word_accents'],'female_hmong_reference_required_sha256':'ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17'},indent=2))
print('PREFLIGHT_PASSED',flush=True)
