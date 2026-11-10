import base64,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent;F=ROOT/'voice/audio/mww'
report=json.loads((F/'render_report.json').read_text());audio=F/report['mp3_file']
assert report['audio_seconds']==1340 and report['mp3_decoded_duration']['verified']
assert report['mp3_decoded_duration']['sample_frames']==64320000
assert report['narration_style_id']=='science-documentary-expressive-v1'
assert report['voice_id']=='hmong-female-3' and report['gender']=='Female'
assert report['reference_sha256']=='ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17'
assert hashlib.sha256(audio.read_bytes()).hexdigest()==report['mp3_sha256']
report.update(native_speed_nominal=1.0,native_speed_range=[.97,1.03],native_speed='varied by phrase',native_phrase_gain_db_range=[-.3,.6],native_pause_seconds_range=[.07,.16],sample_identifier_spoken_form={},native_word_alignment_available=False,translation_review_status='Hmong localisation rewritten by assistant; independent native editorial, listening and White Hmong dialect review pending')
(F/'render_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
manifest=dict(voice_id=report['voice_id'],reference_sha256=report['reference_sha256'],mp3_sha256=report['mp3_sha256'],seconds=1340,narration_style_id=report['narration_style_id'])
payload=ROOT/'native-blob-input.json';payload.write_text(json.dumps(dict(content=base64.b64encode(audio.read_bytes()).decode(),encoding='base64')))
sha=subprocess.check_output(['gh','api','-X','POST','repos/seotro95/seotro/git/blobs','--input',str(payload),'--jq','.sha'],text=True).strip();payload.unlink();assert len(sha)==40
entries=[dict(path='native-baishiya08/'+audio.name,mode='100644',type='blob',sha=sha)]
for name,content in [('render_report.json',json.dumps(report,ensure_ascii=False,indent=2)),('subtitles.srt',(F/'subtitles.srt').read_text()),('manifest.json',json.dumps(manifest,indent=2))]:entries.append(dict(path='native-baishiya08/'+name,mode='100644',type='blob',content=content))
(ROOT/'native-tree-entries.json').write_text(json.dumps(entries,ensure_ascii=False));(ROOT/'NATIVE_READY.json').write_text(json.dumps(dict(blob_sha=sha,manifest=manifest,bytes=audio.stat().st_size),indent=2))
print(json.dumps(dict(blob_sha=sha,sha256=report['mp3_sha256'],seconds=1340,max_tempo=report['max_used_post_tempo'],max_padding_seconds=report['max_cue_padding_seconds'])))
