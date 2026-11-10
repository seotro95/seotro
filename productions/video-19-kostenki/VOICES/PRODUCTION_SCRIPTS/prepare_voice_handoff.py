import json,re,shutil
from pathlib import Path
R=Path(__file__).parent;D=R/'verified-release/details';H=R/'final-handoff';prefix=Path('productions/video-19-kostenki');V=H/prefix/'VOICES';V.mkdir(parents=True,exist_ok=True)
qa=json.loads((R/'VOICE_RELEASE_QA.json').read_text());assert qa['status']=='passed'
archive=json.loads((R/'VOICE_ARCHIVE_QA.json').read_text());assert archive['status']=='passed'
release=json.loads((R/'RELEASE_METADATA.json').read_text());assets={x['name']:x for x in release['assets']};runs=json.loads((R/'TASK_STATE.json').read_text())
for p in D.rglob('*'):
    if p.is_file():dest=V/p.relative_to(D);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
for n in ['ENGLISH_WORD_AUDIT.json','VOICE_RELEASE_QA.json','VOICE_ARCHIVE_QA.json','VOICE_INPUT_QA.json','TRANSLATION_REVIEW.json','DOCUMENT_DELIVERY_STATE.json','TASK_SCOPE_AUTHORIZATION19.json']:
    if (R/n).exists():shutil.copyfile(R/n,V/n)
manifest=json.loads((D/'AUDIO_MANIFEST.json').read_text());by={x['locale']:x for x in manifest['voices']};base='https://github.com/seotro95/seotro/releases/download/kostenki-video-19-20m15s/'
(V/'PROGRESS.json').write_text(json.dumps({'topic':19,'status':'completed17voices_verified_and_published','target_seconds':1215,'voice_count':17,'locales':list(by),'english_run':runs['english_run_id'],'localized_run':runs['locales_run_id'],'release_url':release['html_url'],'public_asset_digests_verified':True,'public_voice_archive_members_verified':True,'independent_native_editorial_listening_review_pending':True},ensure_ascii=False,indent=2))
links='# Tải voice — chủ đề 19 Kostenki\n\n17 MP3 riêng, mỗi bản 20:15. Bản chính dùng voice Anh; 16 giọng nam và H’Mông Trắng nữ 3, giữ ID, engine và mẫu đã khóa.\n\n| Quốc gia/ngôn ngữ | Giọng | TảiMP3 |\n|---|---|---|\n'
for x in manifest['voices']:links+=f'| {x["name"]} | {x["voice_id"]} | [Tải]({base}{x["filename"]}) |\n'
links+=f'\n[ZIP17voice]({base}KOSTENKI_19_17_VOICES_TEN_QUOC_GIA.zip) · [Hồ sơ giọng]({base}KOSTENKI_19_HO_SO_GIONG_TEN_QUOC_GIA.zip) · [Kịch bản/12TXTprompt]({base}KOSTENKI_VIDEO_19_TAI_LIEU_20m15s.zip).\n\nMỗi bản được giải mã58.320.000mẫu48kHz. Anh121mốc10s+5s cuối; bản dịch11chương100s+115s cuối. Khớp chương và tổng thời lượng,không cam kết khớp từng từ giữa ngôn ngữ. Giữ cao độ và ID,nhấn nhá theo câu/cụm. Kiểm tra kỹ thuật không thay cho người bản ngữ nghe/biên tập;H’MôngTrắng chưa được xác nhận phương ngữ độc lập.\n'
(V/'DOWNLOAD_LINKS.md').write_text(links)
P=V/'PRODUCTION_SCRIPTS';P.mkdir(exist_ok=True)
scripts=['audit_english19.py','audit-workflow.yml','repair_english19.py','repair-workflow.yml','PRODUCTION_STEPS_READABLE.md','render_common.py','render_online.py','render_hmong.py','prosody.py','job_init.py','publish_voices_job.py','stage_native.py','prepare_scripts.py','clarify_localizations.py','repair_tree_growth_context.py','repair_animal_sex_context.py','review_vietnamese_full.py','finish_localization_review.py','validate_voice_inputs.py','verify_release.py','verify_voice_archive.py','prepare_voice_handoff.py','stage_english.py','stage_locales.py','vietnamese_reviewed.tsv','hmong_reviewed.tsv','source_integrity.json','BASELINE_VOICE_PROFILES.json','english-workflow.yml','locales-workflow.yml','TASK_SCOPE_AUTHORIZATION19.json']
for n in scripts:shutil.copyfile(R/n,P/n)
for p in (R/'voice/scripts').glob('*.json'):
    if p.stem in by:
        dst=P/'SCRIPTS_INPUT'/p.name;dst.parent.mkdir(exist_ok=True);shutil.copyfile(p,dst)
steps='''# Quy trình áp dụng — chủ đề19 Kostenki,20:15

1. Đọc danh sách100chủ đề đã lưu,chọn đúng19“Nhà bằng xương voi ma mút”. Giữ kết quả1–4,6,8 và các trạng thái khác. Không tự bắt đầu20hay những tập còn trong hàng đợi.
2. Đối chiếu video nguồn người dùng bằngSHA256f1a8659dbccd4db12a79e3c18ea2e1fe08f46f7a03c42bc2250f454f69eff70c. Dùng lời và hình mẫu đã xem để phân tích nhịp vật chứng→câu hỏi→kiểm chứng→bài toán sinh tồn→callback;không sao chép lời,footage,trẻ em,cờ hoặc đồ họa nguồn.
3. Đọc nguồn khoa học riêng choKostenki,Mezhyrich,Gontsy và phương pháp định tuổi. Giữ rõ giả thuyết mái/chức năng,phân biệt tuổi mẫu với lúc xây và thời gian cư trú;giữ30cá thể được xác định giới tính trong39cá thể nghiên cứu,17cái/13đực,không biến thành số người hoặc một cuộc săn.
4. Viết lờiAnh2.816từ,122mốc gồm121×10giây và5giây cuối,tổng1.215giây=20:15.11chương100giây,chương cuối115giây. Câu hỏi dẫn qua quy mô,công sức,mái che,xương cũ,dữ liệu sinh học,lửa,cường độ hoạt động,so sánh di chỉ và ý nghĩa niên đại.
5. Tạo120prompt mới/12TXT,đúng10prompt/tệp,số001–120.2mốc dùng lại được đánh dấu,timelinekhácsốclip. Mỗi prompt tạo10giây,chỉ lấy5giây ở mốc kết. Mỗi prompt kết thúc cùng đoạn bằng“không có âm thanh”.
6. Mỗi cảnh một hành động,một chuyển độngmáy;luân phiên cảnhquan,vậtliệu,ngườilớn,labvàmôhình. Không trẻ em kể cả nền,bóng,phảnchiếu,ảnh,màn hình,tượng,sơđồ. Chỉ trưởngthành35–60tuổi và độngvậttrưởngthành. Không xươngngười,săn giết,máu,nhân vật cổ cụ thể. Mái che là môhìnhgiảnggiải hiện đại;không tự coi là kiến trúcKostenki đã chứng minh.
7. Bàn giaoZIPkịch bản,prompt,SRT,timeline,hook12cảnh/30giây,nguồn và phân tích trước voice. GiữZIPtài liệu gốc bất biến. Kiểm sốmốc,thời lượng,10prompt/tệp,đuôi imlặng,không trẻem và tảikiểmasset.
8. Giữ17ID/engine/pitch/mẫu thamchiếu đã lưu. Loại metadata riêng của tập8 khỏi đầu vào19,chỉ giữ thông tin nhận diện giọng;đặt target1215s cho tập19. Giữ science-documentary-expressive-v1 và tênfiletheoquốcgia.
9. Dịch theo ngữ cảnh chương,làm rõ occupationlà sửdụngdi chỉ,depositslà lớpđất,ringlà vòngxương,killingnóivềvoi ma mút. Rà riêng nghĩa vòngsinhtrưởngcủacây,giới tính độngvật,các số liệu và độ bấtđịnh. Việt/H’Mông có biên tập riêng;ngôn ngữ khác có rà thuật ngữ theo locale. Vẫn cần người bản ngữ biên tập và nghe độc lập.
10. Dùng online_backend,timing,documents củaMelo-Viet1.3.1 đã ghimsourcecommit vàSHA256. Chạy previewAnh30giây,kiểm nhấnnhá/từ/thời lượng rồi tạoAnhđầyđủ. Tạo15bảnnam địa phương trênActions với checkpoint;dùng workflow riêng kostenki-english19.yml và kostenki-locales19.yml,không ghi đèworkflow cũ.
11. H’Mông dùng Voice-Studio-Hmong1.6.6,NativeVITS+OpenVoiceV2,hmong-female-3,mẫuSHA256ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17. Giữclear-v1,tốc độtheocụm0,97–1,03,nhấnnhánhẹ vàgiữcaođộ. Bộ chuẩn hóa gốc xử lý số,không xóa nội dung.
12. CănAnh theo121ô10s+5s cuối,cácbảndịch theo12chương100/115s. Hậu kỳ giữcaođộ,không cắtmấtlời;giớihạn tempoAnh1,4,cácbảnkhác1,5. MỗiMP3giảimã58.320.000mẫu48kHz=20:15. Khớp tổng/chương không có nghĩa khớp từng từgiữangônngữ.
13. Đổi tênquốcgia bằng sao chép nguyênbyte,kiểmSHA256,đủ16nam+1H’Môngnữ. Phát hành17MP3riêng,ZIPtổng,ZIPhồsơ. Đối chiếu digestmáychủ,tảikiểmAnh,cảZIP vàhash17thànhviên,đồngthờilưu báo cáo,timing,lờidịch,IDvàpreset đểtiếptục.

Khi nhậnclip19:mởđầu12shottrong30giâyvoice,khôngcộngintro ngoài20:15,cắt theo ý,dissolve ngắn khi cần. ChỉvoiceAnh,bỏtoànbộtiếngclip,khôngnhạc/SFX;đồhọa/nhãn khoa học làmtrongeditor,không choAIbịa. Kiểmchildpolicy,giải mã,frame,đồngbộ vàlink trước bàn giao video. Hiện chưa nhậnclip và chưa dựngvideo19.

Tập sau phải đọc lại số chủ đề/thời lượng/ranhchương từ yêu cầu mới. Không tái dùng hằng số1215s hoặc thông tin tập19 như mặc định của cả chuỗi.
'''
(H/prefix/'PRODUCTION_STEPS_APPLIED.md').write_text((R/'PRODUCTION_STEPS_READABLE.md').read_text())
readme=(R/'package/README.md').read_text().replace('Tài liệu bàn giao trướcvoice. Bộ17voice giữ16nam vàH’MôngTrắngnữ3,cùngID/style/mẫu đã lưu;thời lượng đích20:15.','Tài liệu đã bàn giao trướcvoice.17MP3 riêng đã được kiểm tra đúng20:15 sau giải mã;16nam,H’MôngTrắngnữ3,cùngID/style/mẫu đã lưu.')
readme+='\n\n[Tải từng voice](VOICES/DOWNLOAD_LINKS.md) · [Quy trình đã áp dụng](PRODUCTION_STEPS_APPLIED.md) · [QA giọng](VOICES/VOICE_RELEASE_QA.json). Các bản dịch và phương ngữH’MôngTrắng vẫn cần người bản ngữ nghe/biên tập độc lập.\n'
(H/prefix/'README.md').write_text(readme)
records=[e for f in R.glob('doc_tree_group_*.json') for e in json.loads(f.read_text())]
state=json.loads(next(e['content'] for e in records if e['path']=='productions/series/SERIES_STATE.json'));old=json.loads((R/'SERIES_STATE.before.json').read_text());done=state.pop('in_progress_topic_19')
done.update(voice_status='17_expressive_voices_delivered_technical_qa_passed_native_review_pending',voice_files_delivered=17,verified_seconds_per_voice=1215,voice_release_tag=release['tag_name'],voice_release_url=release['html_url'],voice_archive_url=assets['KOSTENKI_19_17_VOICES_TEN_QUOC_GIA.zip']['browser_download_url'],voice_archive_sha256=archive['sha256'],voice_details_url=assets['KOSTENKI_19_HO_SO_GIONG_TEN_QUOC_GIA.zip']['browser_download_url'],voice_asset_digests_verified=True,voice_archive_members_verified=True,voice_country_names_delivered=True,voice_workflow_run_ids=list(dict.fromkeys([runs.get('original_english_run_id',runs['english_run_id']),runs['locales_run_id'],runs['english_run_id']])),voice_workflow_run_id=runs['locales_run_id'],voice_workflow_url=f'https://github.com/seotro95/seotro/actions/runs/{runs["locales_run_id"]}',voice_build_branch=runs['voice_build_branch'],translation_native_review_pending=True,white_hmong_dialect_independently_verified=False,english_voice_sha256=by['en-US']['sha256'],native_hmong_sha256=by['mww']['sha256'],native_hmong_reference_sha256='ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17',production_steps_document=str(prefix/'PRODUCTION_STEPS_APPLIED.md'),voice_generation_source_path=str(prefix/'VOICES/PRODUCTION_SCRIPTS'),main_video_audio_language='en-US',video_status='awaiting_episode19_generated_clips',documents_status='delivered',documents_delivered=True)
state.update(completed_topic_19=done,active_topic=None,next_topic_id=old['next_topic_id'],last_requested_topic_id=19)
for i in [1,2,3,4,6,8]:assert state[f'completed_topic_{i}']==old[f'completed_topic_{i}']
for x in state['topics']:
    if x['id']==19:x['status']='documents_and_17_expressive_voices_delivered_video_pending_native_review_pending'
    elif any(o['id']==x['id'] for o in old['topics']):assert x==next(o for o in old['topics'] if o['id']==x['id'])
series=H/'productions/series';series.mkdir(parents=True,exist_ok=True);(series/'SERIES_STATE.json').write_text(json.dumps(state,ensure_ascii=False,indent=2))
for n in ['VOICE_PROFILES_LOCKED.json','NARRATION_STYLE_LOCKED.json','VOICE_FILE_NAMING.json']:shutil.copyfile(D/n,series/n)
bookmark=f'''# Tiếp tục từ đây — chủ đề19 đã có tài liệu và17voice

Kostenki,20:15:2.816từAnh,122mốc gồm121×10giây+5giây cuối;120promptmới/12TXT,10prompt/tệp,2mốcREUSE. Mỗi prompt kết thúc“không có âm thanh”,không có hìnhtrẻem. [Tải voice](video-19-kostenki/VOICES/DOWNLOAD_LINKS.md) · [Quy trình](video-19-kostenki/PRODUCTION_STEPS_APPLIED.md).

17MP3 riêng đã giảimã đúng58.320.000mẫu48kHz;giữ16nam,H’MôngTrắngnữ3 vàID/engine/style/mẫu. Tênfiletheoquốcgia. Anhcăn121ô10s+5s,cácbảndịch11chương100s+115s cuối;không cam kết khớp từngtừgiữangônngữ. Bản dịch/nghe/phươngngữ còn cần ràsoát bảnngữ.

Video19chờclip người dùngtạo. Khi nhận:chỉvoiceAnh,bỏmọitiếngclip,hook12shot/30s nằm trong20:15,không thêm intro. Giữcáctập1–4,6,8 và trạngtháimọitậpkhác;khôngtựbắtđầu20. ĐọcSERIES_STATEvàcấuhình trước khilàmtiếp. Mặc địnhchuỗi20phút;20:15làngoạilệriêng19.

---

Nhật ký trước đó;trạng thái hiện tại nằm ở đầu trang.

'''+(R/'BOOKMARK.before.md').read_text()
(H/'productions/TIEP_TUC_TU_DAY.md').write_text(bookmark)
entries=[dict(path=str(p.relative_to(H)),mode='100644',type='blob',content=p.read_text()) for p in sorted(H.rglob('*')) if p.is_file()]
for e in entries:assert not re.search(r'file_[0-9a-f]{32}|/workspace/attachments/[0-9a-f]{8}-',e['content']),e['path']
groups=[];g=[];count=0
for e in entries:
    n=len(json.dumps(e,ensure_ascii=False).encode())
    if g and count+n>290000:groups.append(g);g=[];count=0
    g.append(e);count+=n
if g:groups.append(g)
for i,g in enumerate(groups):(R/f'voice-handoff-group-{i}.json').write_text(json.dumps(g,ensure_ascii=False))
(R/'VOICE_HANDOFF_STAGING.json').write_text(json.dumps(dict(groups=len(groups),files=len(entries)),indent=2));print((R/'VOICE_HANDOFF_STAGING.json').read_text())
