import hashlib,json,urllib.request
from pathlib import Path
R=Path(__file__).parent
q=json.load(urllib.request.urlopen('https://github.com/seotro95/seotro/releases/download/schoeningen-video-87-20m22s/DOCUMENT_QA.json',timeout=45));assert q['status']=='passed' and q['target_seconds']==1222 and q['unique_prompts']==110
p=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text());assert len(p['profiles'])==17 and sum(v['gender']=='Male' for v in p['profiles'])==16
profiles={v['locale']:v for v in p['profiles']};assert profiles['vi-VN']['voice_id']=='vi-VN-NamMinhNeural' and profiles['mww']['voice_id']=='hmong-female-3'
qa=json.loads((R/'VOICE_INPUT_QA.json').read_text());assert qa['status']=='passed' and qa['target_seconds']==1222
for locale in profiles:
 file=R/'voice/scripts'/f'{locale}.json';assert hashlib.file_digest(file.open('rb'),'sha256').hexdigest()==qa['script_sha256'][locale]
 rows=json.loads(file.read_text());assert len(rows)==(123 if locale=='en-US' else 13) and rows[-1]['end']==1222
 if locale!='en-US':assert (R/'voice/scripts'/f'{locale}.reviewed87').exists()
en=json.loads(Path('preflight_english/render_report.json').read_text());assert en['decoded_frames_48000']==1440000 and en['voice_id']==profiles['en-US']['voice_id'] and en['word_metadata_exact_script_match'] and en['word_boundary_cue_split']
vi=json.loads(Path('preflight_namminh/NAM_MINH_PREFLIGHT_QA.json').read_text());assert vi['status']=='passed' and vi['voice_id']==profiles['vi-VN']['voice_id'] and vi['gender']=='Male' and vi['decoded_frames_48000']==480000 and vi['catalogue_verified']
(R/'VOICE_PREFLIGHT_QA.json').write_text(json.dumps({'status':'passed','topic_id':87,'documents_published':True,'scripts_verified':17,'english_preview_30s_exact_boundaries':True,'actual_namminh_male_catalogue_and_audio_verified':True,'native_hmong_reference_required':profiles['mww']['reference_sha256']},indent=2));print('EPISODE87_PREFLIGHT_PASSED',flush=True)
