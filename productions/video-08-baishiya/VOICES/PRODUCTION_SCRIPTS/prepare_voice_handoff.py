import json,shutil
from pathlib import Path
R=Path(__file__).parent;D=R/'verified-release/details';H=R/'final-handoff';H.mkdir(exist_ok=True)
qa=json.loads((R/'VOICE_RELEASE_QA.json').read_text());assert qa['status']=='passed';release=json.loads((R/'RELEASE_METADATA.json').read_text());assets={x['name']:x for x in release['assets']};prefix=Path('productions/video-08-baishiya');V=H/prefix/'VOICES';V.mkdir(parents=True,exist_ok=True)
for p in D.rglob('*'):
 if p.is_file():dest=V/p.relative_to(D);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,dest)
for n in ['VOICE_RELEASE_QA.json','VOICE_INPUT_QA.json','HMONG_TEXT_VALIDATED.json','TRANSLATION_REVIEW.json','DOCUMENT_DELIVERY_STATE.json','VOICE_WORKFLOW_STATE.json','DOCUMENT_PUBLIC_ASSET_QA.json','VOICE_ARCHIVE_QA.json']:
 if (R/n).exists():shutil.copy(R/n,V/n)
M=json.loads((D/'AUDIO_MANIFEST.json').read_text());by={x['locale']:x for x in M['voices']};base='https://github.com/seotro95/seotro/releases/download/baishiya-video-08-22m20s/'
links='# Tải voice — chủ đề 8 Baishiya\n\n17 MP3 riêng, mỗi bản 22:20. Video chính chỉ dùng tiếng Anh.\n\n| Quốc gia / ngôn ngữ | Giới tính | Tải MP3 |\n|---|---|---|\n'
for m in M['voices']:links+=f'| {m["name"]} | {m["gender"]} | [Tải]({base}{m["filename"]}) |\n'
links+=f'\n[ZIP đủ 17 voice]({base}BAISHIYA_08_17_VOICES_TEN_QUOC_GIA.zip) · [Hồ sơ giọng]({base}BAISHIYA_08_HO_SO_GIONG_TEN_QUOC_GIA.zip) · [Kịch bản và 12 TXT prompt]({base}BAISHIYA_VIDEO_08_TAI_LIEU_22m20s.zip)\n\nĐã kiểm tra thời lượng, mã giọng, giới tính, nhấn nhá, hash, lời Anh và số liệu quan trọng trong bản dịch. Kiểm tra kỹ thuật không thay thế rà soát biên tập/nghe độc lập của người bản ngữ; phương ngữ H’Mông Trắng chưa được xác nhận độc lập.\n';(V/'DOWNLOAD_LINKS.md').write_text(links)
P=V/'PRODUCTION_SCRIPTS';P.mkdir(exist_ok=True)
for n in ['render_common.py','render_online.py','render_hmong.py','prosody.py','job_init.py','publish_voices_job.py','stage_native.py','make_workflow.py','prepare_scripts.py','review_localized.py','apply_hmong_review.py','validate_voice_inputs.py','verify_release.py','prepare_voice_handoff.py','vietnamese_reviewed.tsv','hmong_reviewed.tsv','japanese_reviewed.tsv','source_integrity.json','BASELINE_VOICE_PROFILES.json','english-workflow.yml','locales-workflow.yml']:
 shutil.copy(R/n,P/n)
for n in ['REPAIR_PLAN.json','make_repair_workflow.py','job_init_repair.py','repair-workflow.yml','VOICE_TIMING_REPAIRS.json','LOCALIZATION_REPAIRS.json','EN_CHECKPOINT_PLAN.json','apply_localization_repairs.py','korean_reviewed.tsv','japanese_chapter11_reviewed.txt','collect_original_voices.py','refresh_release_notes.py','publish_available_voices.py','available-workflow.yml','RELEASE_NOTES_FINAL.md','verify_voice_archive.py']:
 if (R/n).exists():shutil.copy(R/n,P/n)
for p in (R/'voice/scripts').iterdir():
 if p.is_file() and '.partial.' not in p.name:
  q=P/('SCRIPTS_INPUT' if p.suffix=='.json' else 'REVIEW_MARKERS')/p.name;q.parent.mkdir(exist_ok=True);shutil.copy(p,q)
steps='''# Quy trình áp dụng — chủ đề 8 Baishiya, 22:20

1. Đọc danh sách 100 chủ đề và trạng thái GitHub. Chọn đúng chủ đề 8 theo yêu cầu, giữ kết quả tập 1–4 và 6; tập 5 và 7 vẫn trong hàng đợi. Không tự bắt đầu tập 9.
2. Đối chiếu video tham khảo bằng SHA256 đã lưu. Học cấu trúc vật chứng nhỏ → câu hỏi lớn → kiểm chứng → bài toán sinh tồn → trở lại vật chứng. Đây là phân tích phong cách dựng, không sao chép lời hay footage, không coi nội dung Yana trong nguồn là dữ kiện Baishiya.
3. Viết lời Anh mới 3.162 từ trong 134 đoạn 10 giây, tổng 1.340 giây. Hai chương đầu 120 giây, mười chương sau 110 giây. Mật độ 22–26 từ mỗi đoạn giúp có chỗ nghỉ và nhấn. Không dùng thời lượng hay ranh chương tập trước.
4. Tạo 120 prompt mới trong 12 TXT, đúng 10 prompt mỗi tệp, số liên tục 001–120. Đánh dấu 14 mốc REUSE và clip nguồn tương ứng trong timeline 134 mốc. Tên clip BS08_001–120 khác số mốc timeline. Mỗi clip một shot liên tục 10 giây, hoàn toàn không âm thanh.
5. Không có trẻ em ở bất kỳ đâu, kể cả nền, bóng, phản chiếu, ảnh, màn hình, tượng hoặc sơ đồ. Người hiện rõ trưởng thành 25–60 tuổi. Không dựng chân dung hay cơ thể chủ hóa thạch. Mô hình xương động vật phải rõ không phải xương người; hàm giảng giải chỉ có răng vĩnh viễn trưởng thành. Động vật hiện trên hình đều trưởng thành.
6. Xen cảnh quan cao nguyên, động vật, vật liệu, thao tác người lớn và phòng thí nghiệm. Cảnh kỹ năng cổ là minh họa vô danh, không gán danh tính hay trang phục Denisovan đã được chứng minh. Không đồ hiện đại trong cảnh cổ. Không dựng bếp lửa Baishiya như sự kiện đã xác nhận. Chữ, bản đồ và số liệu thêm trong editor, không để mô hình video bịa ra.
7. Đối chiếu 13 nguồn và bảng liên kết bằng chứng. Bài chính Xia và cộng sự 2024, Nature, DOI10.1038/s41586-024-07612-9, CC BY4.0, đã ghi công; lời mới, không sao chép hình. Phân biệt mẫu với số cá thể, tuổi tối thiểu với tuổi chết, lớp chứa mẫu với ngày chết, ZooMS sàng lọc với nhận diện protein chi tiết. Gene ở người hiện đại không phải sinh lý đo được của cá nhân Xiahe.
8. Bàn giao ZIP và TXT qua Release Assets trước khi tạo voice. Giữ ZIP tài liệu gốc bất biến. Bản dịch dùng ngữ cảnh chương và thuật ngữ làm rõ. Viết lại toàn bộ 12 chương Việt và H’Mông, cùng bốn chương Nhật; sửa thuật ngữ Tây Ban Nha, Pháp, Hàn và Bồ Đào Nha. Loại câu tiếng Anh còn sót, đối chiếu các giá trị số quan trọng. Rà soát này không thay thế người bản ngữ nghe và biên tập độc lập.
9. Giữ 17 ID của science-prehistory-17-v1: 16 nam, H’Mông Trắng nữ3. Giữ mẫu tham chiếu gốc SHA256 và style science-documentary-expressive-v1. Dùng backend gốc Melo đã ghim mã nguồn; H’Mông dùng VITS+OpenVoiceV2 của tool riêng. Không đổi engine, ID, cao độ hoặc mẫu giọng. Bộ chuẩn hóa gốc H’Mông xử lý số, không xóa chữ số.
10. Kiểm tra preview Anh 30 giây rồi tạo bản Anh đầy đủ. Dùng workflow riêng cho tập8, không ghi đè workflow cũ. Các bản nam địa phương hóa chạy có checkpoint trên Actions; H’Mông native chạy riêng và kiểm mẫu tham chiếu. Dùng thay đổi nhịp, nghỉ và nhấn âm lượng nhẹ. Giữ phần đạt; nếu có lỗi chỉ sửa đoạn hoặc locale cần thiết và vô hiệu hóa đúng cache có thay đổi lời.
11. Căn Anh theo 134 ô 10 giây, bản dịch theo 12 chương 120/110 giây. Giới hạn tempo hậu kỳ Anh 1,4 và các bản khác 1,5; không cắt mất lời. Mỗi bản phải giải mã đúng 64.320.000 mẫu ở48kHz =22:20. Khớp chương và tổng không có nghĩa khớp từng từ giữa mọi ngôn ngữ.
12. Đổi tên theo quốc gia bằng sao chép nguyên byte, kiểm SHA256. Phát hành17MP3 riêng, ZIP tổng và ZIP hồ sơ. Đối chiếu digest máy chủ với báo cáo từng giọng, ID/giới tính/style/thời lượng; đối chiếu đầy đủ3.162 từ/134mốcAnh và giải mã độc lập fileAnh công khai. Lưu script, báo cáo, SRT, preset, mã nguồn, link và trạng thái để tiếp tục.

Chưa dựng video8 vì chưa có clip của tập này. Khi nhận clip: chỉ dùng đúng voiceAnh đã khóa, loại mọi tiếng nguồn, không nhạc/SFX; mở đầu12shot trong30giây voice theoCSV, không thêm intro ngoài22:20. Cắt theo ý, dissolve ngắn khi đổi bối cảnh hoặc quy mô; ưu tiên sự rõ ràng của câu chuyện. Trước dựng cần xem contact sheet tất cả clip, loại cảnh có trẻ em, đồ hiện đại trong cảnh cổ hoặc chữ/số liệu AI bịa. Trước bàn giao video cần kiểm toàn bộ giải mã, frame, một đường tiếng và đồng bộ nhiều điểm.

Ở tập sau, lấy chủ đề/thời lượng/số mốc/ranh chương từ yêu cầu mới. Giữ ID, mẫu giọng, style, tên quốc gia và chính sách không có trẻ em. Không chạy nguyên hằng số của tập8 cho tập khác.
'''
(H/prefix/'PRODUCTION_STEPS_APPLIED.md').write_text(steps)
readme='''# Chủ đề 8 — Baishiya, 22:20

**Baishiya: The Survival Story Hidden in Broken Bones**

Đã bàn giao kịch bản Anh3.162từ/134mốc10giây;120promptmới/12TXT,mỗiTXT10prompt;14mốcREUSEcóđánhdấu. Không trẻ em trong bất kỳ hình nào, chỉ người trưởng thành25–60tuổi, clip hoàn toàn im lặng.

Đã có17MP3 riêng, mỗi bản được kiểm tra đúng22:20 sau giải mã:16nam vàH’MôngTrắngnữ3, cùng ID/style đã lưu. Anh căn134ô10giây; bản dịch hai chương120giây và mười chương110giây. Tên tệp theo quốc gia.

[Tải từng voice](VOICES/DOWNLOAD_LINKS.md) · [Quy trình đã áp dụng](PRODUCTION_STEPS_APPLIED.md) · [QA âm thanh](VOICES/VOICE_RELEASE_QA.json)

Kịch bản sạch/có mốc,SRT,timeline,12TXTprompt,hook30giây và nguồn có trong ZIP tài liệu đã phát hành trước voice. ZIP gốc được giữ bất biến. Quy trình phía trên ghi rõ giới hạn bằng chứng và cách áp dụng cho tập sau. Kiểm tra kỹ thuật đã đạt; bản dịch/nghe và phương ngữH’MôngTrắng còn cần người bản ngữ rà soát độc lập. Chưa cóclip8,chưa dựngvideo8.
'''
(H/prefix/'README.md').write_text(readme)
# Recover the exact document-stage state from the approved staged tree.
records=[e for f in R.glob('doc_tree_group_*.json') for e in json.loads(f.read_text())]
s=json.loads(next(e['content'] for e in records if e['path']=='productions/series/SERIES_STATE.json'));cfg=next(e['content'] for e in records if e['path']=='productions/series/PRODUCTION_DEFAULTS.json');before=json.loads((R/'SERIES_STATE.before.json').read_text());done=s.pop('in_progress_topic_8');runs=json.loads((R/'VOICE_WORKFLOW_STATE.json').read_text());deliveryrun=runs['delivery_workflow_run_id']
done.update(voice_status='17_expressive_voices_delivered_technical_qa_passed_native_review_pending',voice_files_delivered=17,verified_seconds_per_voice=1340,voice_release_tag=release['tag_name'],voice_release_url=release['html_url'],voice_archive_url=assets['BAISHIYA_08_17_VOICES_TEN_QUOC_GIA.zip']['browser_download_url'],voice_archive_sha256=assets['BAISHIYA_08_17_VOICES_TEN_QUOC_GIA.zip']['digest'].split(':')[1],voice_details_url=assets['BAISHIYA_08_HO_SO_GIONG_TEN_QUOC_GIA.zip']['browser_download_url'],voice_asset_digests_verified=True,voice_archive_members_verified=True,voice_country_names_delivered=True,voice_workflow_run_ids=runs['voice_workflow_run_ids'],voice_workflow_run_id=deliveryrun,voice_workflow_url=f'https://github.com/seotro95/seotro/actions/runs/{deliveryrun}',voice_build_branch='codex/baishiya-voice-build-20261110',translation_native_review_pending=True,white_hmong_dialect_independently_verified=False,english_voice_sha256=by['en-US']['sha256'],native_hmong_sha256=by['mww']['sha256'],native_hmong_reference_sha256='ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17',production_steps_document=str(prefix/'PRODUCTION_STEPS_APPLIED.md'),voice_generation_source_path=str(prefix/'VOICES/PRODUCTION_SCRIPTS'),main_video_audio_language='en-US',video_status='awaiting_episode8_generated_clips',documents_status='delivered',documents_delivered=True)
s.update(completed_topic_8=done,active_topic=None,next_topic_id=5,last_requested_topic_id=8,topic5_explicitly_left_queued=True,topic7_explicitly_left_queued=True)
for k in ['completed_topic_1','completed_topic_2','completed_topic_3','completed_topic_4','completed_topic_6']:assert s[k]==before[k],k
for section in ['topics','next_topics']:
 for x in s.get(section,[]):
  if x.get('id')==8:x.update(status='documents_and_17_expressive_voices_delivered_video_pending_native_review_pending',created=True)
  if x.get('id') in [5,7]:assert x['status']=='queued',x
series=H/'productions/series';series.mkdir(parents=True,exist_ok=True);(series/'SERIES_STATE.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n');(series/'PRODUCTION_DEFAULTS.json').write_text(cfg)
for n in ['VOICE_PROFILES_LOCKED.json','NARRATION_STYLE_LOCKED.json','VOICE_FILE_NAMING.json']:shutil.copy(D/n,series/n)
bookmark='''# Tiếp tục từ đây — chủ đề 8 đã có tài liệu và 17 voice

Baishiya, 22:20: 3.162 từ Anh, 134 mốc 10 giây, 120 prompt mới trong 12 TXT và 14 mốc REUSE. [Tải voice](video-08-baishiya/VOICES/DOWNLOAD_LINKS.md) · [Quy trình](video-08-baishiya/PRODUCTION_STEPS_APPLIED.md).

Giữ 16 giọng nam và H’Mông Trắng nữ3 đúng ID, mẫu và style đã khóa; tên tệp theo quốc gia. Mỗi voice 22:20 đã được giải mã và kiểm tra kỹ thuật. Biên tập, nghe và phương ngữ vẫn cần người bản ngữ rà soát độc lập. Không có hình trẻ em.

Video8 chờ clip của chính tập này. Khi nhận clip, chỉ dùng voice Anh, loại tiếng nguồn; hook12shot trong30giây nằm trong22:20, không cộng intro. Giữ kết quả tập1–4 và6. Tập5 và7 vẫn queued; không tự bắt đầu tập9. Đọc trạng thái và cấu hình trước khi làm tiếp. Mặc định chuỗi vẫn20phút;22:20 là ngoại lệ riêng tập8.

---

'''+(R/'BOOKMARK.before.md').read_text();(H/'productions/TIEP_TUC_TU_DAY.md').write_text(bookmark)
entries=[dict(path=str(p.relative_to(H)),mode='100644',type='blob',content=p.read_text()) for p in sorted(H.rglob('*')) if p.is_file()];groups=[];g=[];size=0
for e in entries:
 n=len(json.dumps(e,ensure_ascii=False).encode())
 if g and size+n>330000:groups.append(g);g=[];size=0
 g.append(e);size+=n
if g:groups.append(g)
for i,g in enumerate(groups):(R/f'voice-handoff-group-{i}.json').write_text(json.dumps(g,ensure_ascii=False))
(R/'VOICE_HANDOFF_STAGING.json').write_text(json.dumps(dict(groups=len(groups),files=len(entries)),indent=2));print('Handoff groups',len(groups),'files',len(entries))
