"""Prepare reviewable final records from a fresh canonical-branch snapshot."""
import json,re,shutil
from pathlib import Path
R=Path(__file__).parent
C=R/'canonical_snapshot'
O=R/'canonical_final';O.mkdir(exist_ok=True)
qa=json.loads((R/'PUBLIC_DOWNLOAD_QA.json').read_text())
dqa=json.loads((R/'DOCUMENT_PUBLIC_DOWNLOAD_QA.json').read_text())
assert qa['status']==dqa['status']=='passed' and qa['voice_count']==17
state=json.loads((C/'SERIES_STATE.json').read_text())
assert state['active_topic']['id']==45,'Preserve a different active episode and reconcile manually'
base='https://github.com/seotro95/seotro/releases/download/food-preservation-video-45-20m42s/'
status={**state['active_topic'],'phase':'documents_and17voices_delivered_awaiting_footage','documents_delivered':True,'voices_generated':True,'voice_files_delivered':17,'verified_seconds_per_voice':1242,'decoded_frames_per_voice_48000':59616000,'public_download_verified':True,'documents_zip_sha256':dqa['documents_zip_sha256'],'voice_archive_sha256':qa['public_voice_archive_sha256'],'voice_archive_url':base+'FOOD_PRESERVATION_45_17_VOICES_20m42s.zip','documents_url':base+'FOOD_PRESERVATION_45_TAI_LIEU_20m42s.zip','titles_thumbnail_url':base+'5_TIEU_DE_VA_THUMBNAIL.txt','release_url':'https://github.com/seotro95/seotro/releases/tag/food-preservation-video-45-20m42s','footage_generated':False,'video_rendered':False,'translation_native_review_pending':True,'white_hmong_dialect_independently_verified':False}
state['active_topic']=status;state['completed_topic_45']=status.copy();state['latest_completed_topic_id']=45;state['auto_start_next_topic']=False
topic=next(t for t in state['topics'] if t['id']==45);topic.update(status='documents_and17voices_delivered_public_download_verified_native_review_pending',target_seconds=1242,created=True)
prefs=state['user_preferences'];prefs.update(vietnamese_requested_voice='Adam',vietnamese_voice_change_applies_from_topic=45,narration_style_id='science-documentary-expressive-v2-grouped-English-Adam-VI',voice_naming_profile_id='country-filenames-vi-v2-adam',english_request_group_max_cues=3)
state['handoff_next_action']='Topic45 documents and17voices are complete and publicly reverified. Wait for topic45 generated clips before editing. Keep Adam for future Vietnamese narration and the other16 voice identities. Main video English only;10 relevant shots in first30seconds inside20:42. Do not auto-start another topic or regenerate finished voices.'
def write(name,value):(O/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
write('SERIES_STATE.json',state);write('PRODUCTION_STATUS.json',status)
profile=json.loads((R/'VOICE_PROFILES_LOCKED.json').read_text());assert profile['profile_set_id']=='science-prehistory-17-v2-adam-vi'
write('SHARED_VOICE_PROFILES_LOCKED.json',profile)
naming=json.loads((C/'VOICE_FILE_NAMING.json').read_text());naming['naming_profile_id']='country-filenames-vi-v2-adam';vi=next(p for p in naming['voices'] if p['locale']=='vi-VN');vi.update(display_name='Việt Nam — Adam',delivery_slug='Viet_Nam_Adam');naming['revision_note']='Vietnamese changes to native Adam from requested topic45; prior episode filenames stay unchanged.';write('VOICE_FILE_NAMING.json',naming)
defaults=json.loads((C/'PRODUCTION_DEFAULTS.json').read_text());defaults.update(voice_profile_set_id=profile['profile_set_id'],narration_style_id=prefs['narration_style_id'],voice_naming_profile_id=naming['naming_profile_id'])
defaults['episode_specific_overrides']['45']={'target_seconds':1242,'english_cues':125,'last_cue_seconds':2,'translated_chapter_seconds':[100]*12+[42],'unique_prompts':110,'reused_slots':15,'vietnamese_voice':'Adam','reason':'Explicit topic45 request; all other completed episodes and queued topics preserved'}
defaults['opening_current_default']={'seconds':30,'shots':10,'adds_runtime':False};write('PRODUCTION_DEFAULTS.json',defaults)
style=json.loads((C/'NARRATION_STYLE_LOCKED.json').read_text());style.update(style_id=prefs['narration_style_id'],applies_to='Topic45 and later unless explicitly changed',identity='Native Vietnamese Adam from topic45; the other16 saved voice identities and Hmong female-3 reference retained',timing='Use latest explicitly requested episode duration. Topic45:1242seconds, English125cues and other languages13shared chapters. No cross-language word alignment claim.')
style['english']={'request_group_max_cues':3,'native_rate':'+0%','word_boundary_exact_text_check':True,'split_back_into_scripted_cues':True,'word_accent_db':1.2,'max_accents_per_cue':2,'pitch_shift':False}
style['vietnamese']={'voice_id':'Adam','region':'Southern Vietnam','engine':'Melo1.3.1worker / VieNeu3.8.3 native ONNX FP32','preset_sha256':next(p for p in profile['profiles'] if p['locale']=='vi-VN')['preset_sha256'],'method':'Native punctuation, small phrase pauses and pitch-preserving chapter fit'}
write('SHARED_NARRATION_STYLE_LOCKED.json',style)
manifest=json.loads((R/'AUDIO_MANIFEST.json').read_text())
links='# Chủ đề 45 — tải tài liệu và 17 giọng 20:42\n\n[Tải đủ 17 giọng ZIP]('+status['voice_archive_url']+') · [Tài liệu và 11 TXT prompt]('+status['documents_url']+') · [5 tiêu đề và 5 prompt thumbnail]('+status['titles_thumbnail_url']+')\n\n'
for v in manifest['voices']:links+='- ['+v['name']+']('+v['url']+') — 20:42\n'
links+='\nBản Việt dùng Adam thật; H’mông dùng female-3. Kỹ thuật giải mã, hash và thời lượng đã kiểm; biên tập/nghe bản ngữ và xác minh phương ngữ H’mông Trắng chưa được thực hiện độc lập.\n';(O/'DOWNLOAD_LINKS.md').write_text(links)
block='<!-- active-production -->\n# Chủ đề 45 — đã có tài liệu và đủ17voice20:42\n\n'+links+'\nChưa có footage hoặc MP4 tập45. Khi có clip: chỉ voice Anh, bỏ toàn bộ tiếng clip,10 cảnh liên quan trong 30 giây đầu nằm trong 20:42. Cảnh thiếu dùng video chuyển động liên quan, không ảnh tĩnh/thẻ chữ. Giữ Adam cho bản Việt các tập sau và 16 nhận diện khác. Không tạo lại voice đã xong hoặc tự bắt đầu tập khác. Hồ sơ: productions/video-45-food-preservation; mã nguồn: nhánh codex/food-preservation45-production-20261112, thư mục episode45.\n<!-- /active-production -->'
resume=(C/'TIEP_TUC_TU_DAY.md').read_text();assert '<!-- active-production -->' in resume;(O/'TIEP_TUC_TU_DAY.md').write_text(re.sub(r'<!-- active-production -->[\s\S]*?<!-- /active-production -->',lambda m:block,resume,count=1))
local=json.loads((R/'TASK_STATE.json').read_text());local.update(phase=status['phase'],voices_generated=True,voice_files_delivered=17,public_download_verified=True,voice_archive_sha256=qa['public_voice_archive_sha256'],documents_archive_sha256=dqa['documents_zip_sha256']);(R/'TASK_STATE.json').write_text(json.dumps(local,ensure_ascii=False,indent=2))
print('Canonical topic45 records prepared from verified delivery; no GitHub write performed.')
