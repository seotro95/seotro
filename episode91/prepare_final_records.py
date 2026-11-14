"""Canonical completion from public QA; retain all previous productions."""
from pathlib import Path
import json,re
R=Path(__file__).parent;C=R/'canonical_snapshot';O=R/'canonical_final';O.mkdir(exist_ok=True)
qa=json.loads((R/'PUBLIC_DOWNLOAD_QA.json').read_text());dq=json.loads((R/'DOCUMENT_PUBLIC_DOWNLOAD_QA.json').read_text())
assert qa['status']==dq['status']=='passed' and qa['voice_count']==17 and qa['target_seconds']==1332
state=json.loads((C/'SERIES_STATE.json').read_text());assert state['active_topic']['id']==91
base='https://github.com/seotro95/seotro/releases/download/saqqaq-hair-video-91-22m12s/'
status={**state['active_topic'],'phase':'documents_and17voices_delivered_awaiting_footage','documents_delivered':True,'voices_generated':True,'voice_files_delivered':17,'verified_seconds_per_voice':1332,'decoded_frames_per_voice_48000':63936000,'public_download_verified':True,'documents_zip_sha256':dq['documents_zip_sha256'],'voice_archive_sha256':qa['public_voice_archive_sha256'],'voice_archive_url':base+'SAQQAQ_HAIR_91_17_VOICES_22m12s.zip','documents_url':base+'SAQQAQ_HAIR_91_TAI_LIEU_22m12s.zip?v='+dq['documents_zip_sha256'],'titles_thumbnail_url':base+'5_TIEU_DE_VA_THUMBNAIL.txt','release_url':'https://github.com/seotro95/seotro/releases/tag/saqqaq-hair-video-91-22m12s','footage_generated':False,'video_rendered':False,'translation_native_review_pending':True,'white_hmong_dialect_independently_verified':False}
status.update(json.loads((R/'FINAL_WORKFLOW_RECORDS.json').read_text()))
state['active_topic']=status;state['completed_topic_91']=status.copy();state['latest_completed_topic_id']=91;state['auto_start_next_topic']=False
next(t for t in state['topics'] if t['id']==91).update(status='documents_and17voices_delivered_public_download_verified_native_review_pending',target_seconds=1332,created=True)
assert state['completed_topic_87']['id']==87 and len(state['topics'])==100
state['handoff_next_action']='Topic91 documents and17voices complete,publicly reverified. Wait for new91footage before editing. Keep all17IDs from71 including actual male NamMinh and native Hmongfemale3. Main film Englishonly;10relevant shots in first30seconds within total22:12. Missing clips use related moving video,no still/textcards,no minors. Do not auto-start another topic or regenerate completed voices. Completed87 and all previous productions/backlog preserved.'
def write(name,obj):(O/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
write('SERIES_STATE.json',state);write('PRODUCTION_STATUS.json',status)
profiles=json.loads((R/'VOICE_PROFILES_LOCKED.json').read_text());baseline=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text())
assert {p['locale']:p['voice_id'] for p in profiles['profiles']}=={p['locale']:p['voice_id'] for p in baseline['profiles']}
assert next(p for p in profiles['profiles'] if p['locale']=='vi-VN')['voice_id']=='vi-VN-NamMinhNeural';write('SHARED_VOICE_PROFILES_LOCKED.json',profiles)
naming=json.loads((C/'VOICE_FILE_NAMING.json').read_text());assert next(p for p in naming['voices'] if p['locale']=='vi-VN')['delivery_slug']=='Viet_Nam_Nam_Minh';write('VOICE_FILE_NAMING.json',naming)
defaults=json.loads((C/'PRODUCTION_DEFAULTS.json').read_text());assert defaults['episode_specific_overrides']['91']['target_seconds']==1332 and defaults['episode_specific_overrides']['87']['target_seconds']==1222;write('PRODUCTION_DEFAULTS.json',defaults)
style=json.loads((C/'NARRATION_STYLE_LOCKED.json').read_text());assert style['vietnamese']['voice_id']=='vi-VN-NamMinhNeural';write('SHARED_NARRATION_STYLE_LOCKED.json',style)
manifest=json.loads((R/'AUDIO_MANIFEST.json').read_text())
body=f"[Tải đủ17giọng ZIP]({status['voice_archive_url']}) · [Kịch bản và12TXTprompt]({status['documents_url']}) · [5tiêu đề và5promptthumbnail]({status['titles_thumbnail_url']})\n\n"
for voice in manifest['voices']:body+=f"- [{voice['name']}]({voice['url']}) —22:12\n"
body+='\nĐã tải lại,kiểm hash và giải mã từng MP3 đúng63.936.000mẫu ở48kHz. Giữ17ID từ tập71; Việt NamMinh thật,H’mông female-3. Chưa có kiểm nghe/biên tập bản ngữ độc lập hoặc xác minh phương ngữ H’mông Trắng độc lập.\n'
for old_text,new_text in [('đủ17giọng','đủ 17 giọng'),('và12TXTprompt','và 12 TXT prompt'),('5tiêu đề và5promptthumbnail','5 tiêu đề và 5 prompt thumbnail'),('—22:12','— 22:12'),('lại,kiểm','lại, kiểm'),('đúng63.936.000mẫu ở48kHz','đúng 63.936.000 mẫu ở 48 kHz'),('Giữ17ID từ tập71','Giữ 17 ID từ tập 71'),('thật,H’mông','thật, H’mông')]:body=body.replace(old_text,new_text)
(O/'DOWNLOAD_LINKS.md').write_text('# Chủ đề 91 — tải tài liệu và 17 giọng —22:12\n\n'+body)
block='<!-- active-production -->\n# Chủ đề 91 — tài liệu và17voice22:12 đã kiểm tải\n\n'+body+'''\nChủ đề: tócSaqqaq,ADN và lịch sử cư dân Bắc Cực.3.703từ Anh,134mốc,120prompt mới trong12TXT,14mốc dùng lại. Mỗi prompt cấm trẻ em,thiếu niên,lời nói và âm thanh. Tóc,mô hình,cảnh là minh họa,không dữ liệu đo hoặc chân dung xác thực. Phân biệt công bố2008/2010/2014/2019 và tuổi tóc với tuổi di cư.

Chưa có footage hoặcMP4tập91. Khi có clip: chỉvoiceAnh,xóa tiếngclip,10cảnh/30giây đầu nằm trong22:12; thiếu cảnh dùng video chuyển động liên quan,không ảnh tĩnh/thẻ chữ. Giữ hồ sơ v3NamMinh từ tập71; không tự tạo lại voice hoặc bắt đầu tập khác. Hồ sơ:productions/video-91-saqqaq-hair. Mã nguồn:nhánh codex/saqqaq-hair91-production-20261113,thư mục episode91. Tập87 và toàn bộ các tập trước được giữ nguyên.
<!-- /active-production -->'''
for old_text,new_text in [('và17voice22:12','và 17 voice 22:12'),('tócSaqqaq,ADN','tóc Saqqaq, ADN'),('Cực.3.703từ','Cực. 3.703 từ'),('Anh,134mốc,120prompt','Anh, 134 mốc, 120 prompt'),('trong12TXT,14mốc','trong 12 TXT, 14 mốc'),('em,thiếu','em, thiếu'),('niên,lời','niên, lời'),('Tóc,mô hình,cảnh','Tóc, mô hình, cảnh'),('họa,không','họa, không'),('công bố2008','công bố 2008'),('hoặcMP4tập91','hoặc MP4 tập91'),('chỉvoiceAnh,xóa tiếngclip,10cảnh/30giây','chỉ voice Anh, xóa tiếng clip,10 cảnh/30 giây'),('trong22:12','trong22:12'),('quan,không','quan, không'),('v3NamMinh từ tập71','v3 Nam Minh từ tập71'),('sơ:productions','sơ: productions'),('nguồn:nhánh','nguồn: nhánh'),('20261113,thư','20261113, thư'),('Tập87','Tập87')]:block=block.replace(old_text,new_text)
resume=(C/'TIEP_TUC_TU_DAY.md').read_text();assert '<!-- active-production -->' in resume;(O/'TIEP_TUC_TU_DAY.md').write_text(re.sub(r'<!-- active-production -->[\s\S]*?<!-- /active-production -->',lambda match:block,resume,count=1))
(R/'TASK_STATE.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print('Final91records prepared from public QA;87and all earlier data retained')
