import hashlib,json,urllib.request
from pathlib import Path
R=Path(__file__).parent
q=json.load(urllib.request.urlopen('https://github.com/seotro95/seotro/releases/download/bone-traces-video-58-22m42s/DOCUMENT_QA.json',timeout=45));assert q['status']=='passed' and q['target_seconds']==1362 and q['unique_prompts']==130
p=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text());assert len(p['profiles'])==17 and sum(v['gender']=='Male' for v in p['profiles'])==16
profiles={v['locale']:v for v in p['profiles']};assert profiles['vi-VN']['voice_id']=='Adam' and profiles['mww']['voice_id']=='hmong-female-3'
qa=json.loads((R/'VOICE_INPUT_QA.json').read_text());assert qa['status']=='passed' and qa['target_seconds']==1362
for locale in profiles:
 file=R/'voice/scripts'/f'{locale}.json';assert hashlib.file_digest(file.open('rb'),'sha256').hexdigest()==qa['script_sha256'][locale]
 rows=json.loads(file.read_text());assert len(rows)==(137 if locale=='en-US' else 13) and rows[-1]['end']==1362
 if locale!='en-US':assert (R/'voice/scripts'/f'{locale}.reviewed58').exists()
en=json.loads(Path('preflight_english/render_report.json').read_text());assert en['decoded_frames_48000']==1440000 and en['voice_id']==profiles['en-US']['voice_id'] and en['word_metadata_exact_script_match'] and en['word_boundary_cue_split']
adam=json.loads(Path('preflight_adam/ADAM_PREFLIGHT_QA.json').read_text());assert adam['status']=='passed' and adam['voice_id']=='Adam' and adam['preset_sha256']==profiles['vi-VN']['preset_sha256']
(R/'VOICE_PREFLIGHT_QA.json').write_text(json.dumps({'status':'passed','topic_id':58,'documents_published':True,'scripts_verified':17,'english_preview_30s_exact_boundaries':True,'native_adam_verified':True,'native_hmong_reference_required':profiles['mww']['reference_sha256']},indent=2));print('EPISODE58_PREFLIGHT_PASSED',flush=True)
