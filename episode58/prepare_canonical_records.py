"""Prepare final topic58 records from verified downloads and a fresh branch snapshot."""
import json,re
from pathlib import Path
R=Path(__file__).parent;C=R/'canonical_snapshot';O=R/'canonical_final';O.mkdir(exist_ok=True)
qa=json.loads((R/'PUBLIC_DOWNLOAD_QA.json').read_text());dq=json.loads((R/'DOCUMENT_PUBLIC_DOWNLOAD_QA.json').read_text())
assert qa['status']==dq['status']=='passed' and qa['voice_count']==17 and qa['target_seconds']==1362
state=json.loads((C/'SERIES_STATE.json').read_text());assert state['active_topic']['id']==58,'Reconcile a different active topic before writing'
base='https://github.com/seotro95/seotro/releases/download/bone-traces-video-58-22m42s/'
status={**state['active_topic'],'phase':'documents_and17voices_delivered_awaiting_footage','documents_delivered':True,'voices_generated':True,'voice_files_delivered':17,'verified_seconds_per_voice':1362,'decoded_frames_per_voice_48000':65376000,'public_download_verified':True,'documents_zip_sha256':dq['documents_zip_sha256'],'voice_archive_sha256':qa['public_voice_archive_sha256'],'voice_archive_url':base+'BONE_TRACES_58_17_VOICES_22m42s.zip','documents_url':base+'BONE_TRACES_58_TAI_LIEU_22m42s.zip','titles_thumbnail_url':base+'5_TIEU_DE_VA_THUMBNAIL.txt','release_url':'https://github.com/seotro95/seotro/releases/tag/bone-traces-video-58-22m42s','footage_generated':False,'video_rendered':False,'translation_native_review_pending':True,'white_hmong_dialect_independently_verified':False}
state['active_topic']=status;state['completed_topic_58']=status.copy();state['latest_completed_topic_id']=58;state['auto_start_next_topic']=False
topic=next(t for t in state['topics'] if t['id']==58);topic.update(status='documents_and17voices_delivered_public_download_verified_native_review_pending',target_seconds=1362,created=True)
state['handoff_next_action']='Topic58 documents and17voices are complete and publicly reverified. Wait for topic58 generated clips before editing. Keep the same17voice identities from topic45, including actual Vietnamese Adam and native Hmong female-3. Main video English only;10relevant shots in the existing first30seconds inside22:42. Do not auto-start another topic or regenerate finished voices.'
def write(n,v):(O/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
write('SERIES_STATE.json',state);write('PRODUCTION_STATUS.json',status)
profile=json.loads((R/'VOICE_PROFILES_LOCKED.json').read_text());baseline=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text())
assert {p['locale']:p['voice_id'] for p in profile['profiles']}=={p['locale']:p['voice_id'] for p in baseline['profiles']}
write('SHARED_VOICE_PROFILES_LOCKED.json',profile)
naming=json.loads((C/'VOICE_FILE_NAMING.json').read_text());assert next(v for v in naming['voices'] if v['locale']=='vi-VN')['delivery_slug']=='Viet_Nam_Adam';write('VOICE_FILE_NAMING.json',naming)
defaults=json.loads((C/'PRODUCTION_DEFAULTS.json').read_text());defaults['episode_specific_overrides']['58']={'target_seconds':1362,'english_cues':137,'last_cue_seconds':2,'translated_chapter_seconds':[110]*12+[42],'unique_prompts':130,'reused_slots':7,'vietnamese_voice':'Adam','reason':'Explicit topic58 request; preserve all other episodes and queued topics'}
write('PRODUCTION_DEFAULTS.json',defaults)
style=json.loads((C/'NARRATION_STYLE_LOCKED.json').read_text());style['timing']='Use the latest explicit episode duration. Topic58:1362seconds, English137cues and other languages13shared chapters. No cross-language word-alignment claim.';write('SHARED_NARRATION_STYLE_LOCKED.json',style)
manifest=json.loads((R/'AUDIO_MANIFEST.json').read_text())
body='[Tải đủ 17 giọng ZIP]('+status['voice_archive_url']+') · [Kịch bản và 13 TXT prompt]('+status['documents_url']+') · [5 tiêu đề và 5 prompt thumbnail]('+status['titles_thumbnail_url']+')\n\n'
for v in manifest['voices']:body+='- ['+v['name']+']('+v['url']+') — 22:42\n'
body+='\nMỗi MP3 đã được tải lại, kiểm hash và giải mã đúng 65.376.000 mẫu ở 48 kHz. Việt dùng Adam thật; H’mông dùng reference female-3. Chưa có kiểm nghe/biên tập bản ngữ độc lập hoặc xác minh phương ngữ H’mông Trắng độc lập.\n'
(O/'DOWNLOAD_LINKS.md').write_text('# Chủ đề 58 — tải tài liệu và 17 giọng — 22:42\n\n'+body)
block='<!-- active-production -->\n# Chủ đề 58 — đã có tài liệu và đủ 17 voice 22:42\n\n'+body+'\nChủ đề: nhận diện dấu thú ăn thịt trên xương trước khi kết luận có người săn. Có 137 mốc Anh, 130 prompt mới trong 13 TXT, 7 mốc dùng lại; mọi prompt không có trẻ em, lời nói hoặc âm thanh. Chưa có footage hoặc MP4 tập58. Khi có clip: chỉ voice Anh, bỏ toàn bộ tiếng clip, 10 cảnh liên quan trong 30 giây đầu nằm trong 22:42. Cảnh thiếu dùng video chuyển động liên quan, không ảnh tĩnh hoặc thẻ chữ. Giữ 17 nhận diện như tập45, không tạo lại voice đã xong hoặc tự bắt đầu tập khác. Hồ sơ: productions/video-58-bone-traces; mã nguồn: nhánh codex/bone-traces58-production-20261112, thư mục episode58.\n<!-- /active-production -->'
resume=(C/'TIEP_TUC_TU_DAY.md').read_text();assert '<!-- active-production -->' in resume
(O/'TIEP_TUC_TU_DAY.md').write_text(re.sub(r'<!-- active-production -->[\s\S]*?<!-- /active-production -->',lambda m:block,resume,count=1))
local=json.loads((R/'TASK_STATE.json').read_text());local.update(phase=status['phase'],voices_generated=True,voice_files_delivered=17,public_download_verified=True,voice_archive_sha256=qa['public_voice_archive_sha256'],documents_archive_sha256=dq['documents_zip_sha256']);(R/'TASK_STATE.json').write_text(json.dumps(local,ensure_ascii=False,indent=2))
print('Topic58 canonical records prepared from verified public delivery; no GitHub write performed.')
