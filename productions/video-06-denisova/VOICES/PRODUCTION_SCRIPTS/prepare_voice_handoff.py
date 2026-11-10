import json,shutil
from pathlib import Path
R=Path(__file__).parent;D=R/'verified-release/details';H=R/'final-handoff';H.mkdir(exist_ok=True)
qa=json.load(open(R/'VOICE_RELEASE_QA.json'));assert qa['status']=='passed'
release=json.load(open(R/'RELEASE_METADATA.json'));assets={x['name']:x for x in release['assets']}
prefix=Path('productions/video-06-denisova');V=H/prefix/'VOICES';V.mkdir(parents=True,exist_ok=True)
for p in D.rglob('*'):
 if p.is_file():
  dest=V/p.relative_to(D);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,dest)
for n in ['VOICE_RELEASE_QA.json','VOICE_INPUT_QA.json','HMONG_INPUT_VALIDATION.json','TRANSLATION_COMPLETENESS_QA.json','VOICE_TIMING_REPAIRS.json','CHECKPOINT_DURATION_DIAGNOSTICS.json','DE_CHECKPOINT_DURATION_DIAGNOSTICS.json','EN_KO_IT_CHECKPOINT_DURATION_DIAGNOSTICS.json']:shutil.copy(R/n,V/n)
M=json.load(open(D/'AUDIO_MANIFEST.json'));by={x['locale']:x for x in M['voices']};base='https://github.com/seotro95/seotro/releases/download/denisova-video-06-21min/'
links='# Tải voice — chủ đề 6 Denisova\n\n17 MP3 riêng, mỗi bản 21:00. Video chính chỉ dùng tiếng Anh.\n\n| Quốc gia/ngôn ngữ | Giới tính | Tải MP3 |\n|---|---|---|\n'
for m in M['voices']:links+=f'| {m["name"]} | {m["gender"]} | [Tải]({base}{m["filename"]}) |\n'
links+=f'\n[ZIP đủ 17 voice]({base}DENISOVA_06_17_VOICES_TEN_QUOC_GIA.zip) · [Hồ sơ giọng]({base}DENISOVA_06_HO_SO_GIONG_TEN_QUOC_GIA.zip)\n\nĐã kiểm tra thời lượng, mã giọng, nhấn nhá, hash và lời Anh. Bản dịch, nghe và phương ngữ H’Mông Trắng cần người bản ngữ rà soát độc lập.\n'
(V/'DOWNLOAD_LINKS.md').write_text(links)
P=V/'PRODUCTION_SCRIPTS';P.mkdir(exist_ok=True)
for n in ['render_common.py','render_online.py','render_hmong.py','prosody.py','job_init.py','publish_voices_job.py','stage_native.py','make_workflow.py','prepare_scripts.py','review_translation_sources.py','audit_backtranslations.py','apply_reviewed_chapters.py','validate_voice_inputs.py','verify_release.py','prepare_voice_handoff.py','vietnamese_reviewed_chapters.txt','hmong_reviewed_chapters.txt','VOICE_WORKFLOW_STATE.json','DOCUMENT_DELIVERY_STATE.json','BASELINE_VOICE_PROFILES.json']:
 shutil.copy(R/n,P/n)
for f in R.glob('*_chapter*_reviewed.txt'):shutil.copy(f,P/f.name)
for n in ['make_repair_workflow.py','REPAIR_PLAN.json','GITHUB_ACTIONS_REPAIR_WORKFLOW.yml','ORIGINAL_JOBS_FINAL.json']:
 if (R/n).exists():shutil.copy(R/n,P/n)
if (R/'job_init_repair.py').exists():
 shutil.copy(R/'job_init.py',P/'job_init_original.py');shutil.copy(R/'job_init_repair.py',P/'job_init.py')
shutil.copy(R/'github-build/input/source_integrity.json',P/'source_integrity.json');shutil.copy(R/'github-build/.github/workflows/siberia-final-voices.yml',P/'GITHUB_ACTIONS_BUILD_WORKFLOW.yml')
for n in ['SCRIPTS_INPUT','REVIEW_MARKERS']:(P/n).mkdir(exist_ok=True)
for p in (R/'voice/scripts').iterdir():
 if p.is_file():shutil.copy(p,P/('SCRIPTS_INPUT' if p.suffix=='.json' else 'REVIEW_MARKERS')/p.name)
steps='''# Quy trình đã áp dụng — chủ đề 6 Denisova

1. Đọc trạng thái đã lưu, chọn đúng chủ đề 6 theo yêu cầu; giữ nguyên tập 1–4 đã bàn giao và tập 5 đang xếp hàng. Không tự bắt đầu tập 7.
2. Đối chiếu video nguồn bằng SHA256. Phân tích cách mở đầu bằng vật chứng nhỏ, đặt câu hỏi, chuyển giữa cảnh vĩ mô, môi trường, bản đồ và phòng thí nghiệm; học nhịp dựng và viết lời mới từ nguồn khoa học.
3. Kịch bản Anh mới 3425 từ, 126 đoạn 10 giây, tổng 1260 giây. 12 chương có ranh thật: sáu chương 110 giây rồi sáu chương 100 giây. Không dùng thời lượng hoặc ranh chương của tập trước.
4. Tạo 110 prompt mới, đánh số liên tục trong 11 TXT, mỗi TXT 10 prompt. Đánh dấu 16 ô REUSE và nguồn clip trong timeline 126 cảnh; không yêu cầu tạo lại các ô đó. Mỗi clip 10 giây hoàn toàn im lặng.
5. Không có trẻ em ở bất kỳ vị trí nào: nền, bóng, phản chiếu, ảnh, màn hình, tượng. Chỉ người trưởng thành rõ 25–60 tuổi. Không dựng chủ mẫu Denisova 3/11; chỉ vật chứng mô phỏng rời và người lớn minh họa. Chỉ dùng răng vĩnh viễn trưởng thành trong mô hình giảng giải nha khoa. Không đặt đồ hiện đại trong cảnh cổ.
6. Đối chiếu 27 nguồn, phân biệt DNA ty thể, DNA nhân và protein, giới hạn tuổi tối thiểu, liên hệ phân tử và tên phân loại; không suy ra mặt/ngôn ngữ/tiểu sử từ một mẫu. Bốn bản đồ hiện đại không phải đường bờ cổ hoặc lộ trình di cư. Ba sơ đồ là giảng giải, không phải dữ liệu đo.
7. Phát hành tài liệu trước voice, giữ ZIP gốc bất biến. 16 bản dịch giữ ý, kiểm tra thuật ngữ và số. Viết lại toàn bộ 12 chương Việt và H’Mông; làm rõ các đoạn dễ dịch sai ở 14 locale và kiểm tra dịch ngược các chương 2/4/5/10. Dùng cách viết của Bồ Đào Nha cho pt-PT. Việc này không thay thế biên tập/nghe độc lập của người bản ngữ.
8. Giữ đúng 17 ID của science-prehistory-17-v1: 16 nam, H’Mông nữ 3, cùng mẫu tham chiếu gốc SHA256 và style science-documentary-expressive-v1. Dùng backend Melo đã ghim mã nguồn; H’Mông dùng VITS+OpenVoiceV2 của tool riêng. H’Mông tách chữ/số trước bộ chuẩn hóa số của tool, không xóa số hoặc thay engine.
9. Preview Anh 30 giây, rồi chạy 16 locale trên GitHub Actions có checkpoint; H’Mông native chạy riêng. Dùng nhịp, nghỉ và nhấn âm lượng nhẹ; không đổi cao độ. Chỉ xử lý lại phần lỗi nếu có; giữ đầu vào đã rà soát.
10. Khi đo thực tế, giữ các locale/chương đã đạt và chỉ sửa phần vượt thời lượng. Đo checkpoint trước khi sửa; Nhật chương 8 được viết lại hoàn toàn vì còn lẫn tiếng Anh. Giữ nguyên 3425 từ Anh: riêng 11 ô dùng một yêu cầu trọn ô, tốc độ trong khoảng style cũ và chỉ bỏ khoảng lặng bằng số 0 ở mép, chừa 30 ms; không cắt mẫu tiếng nói. Căn Anh theo 126 ô 10 giây; bản dịch theo 12 chương 110/100 giây. Giới hạn tempo sau tổng hợp: Anh 1,4, các bản khác 1,5. Không cắt lời. Mỗi bản giải mã đúng 60.480.000 mẫu tại 48 kHz = 21:00. Khớp chương/tổng không có nghĩa khớp từng từ giữa mọi ngôn ngữ.
11. Đổi tên theo quốc gia bằng sao chép nguyên byte, kiểm SHA256, phát hành 17 MP3 riêng và ZIP tổng/hồ sơ. Kiểm 17 digest từ máy chủ với báo cáo, đúng ID/giới tính/style/thời lượng, toàn bộ 3425 từ/126 cue Anh và giải mã độc lập file Anh công khai.
12. Lưu script 17 locale, timing, báo cáo, hồ sơ giọng, link tải, mã nguồn và trạng thái để tiếp tục. Chưa dựng video tập 6 vì chưa có clip của tập này. Khi có clip: dùng đúng voice Anh đã khóa, bỏ mọi âm thanh clip, mở đầu 12 shot/30 giây nằm trong 21 phút, không cộng intro.

Khi làm tập sau, lấy thời lượng/chủ đề/số cảnh/ranh chương từ yêu cầu mới và trạng thái; giữ hồ sơ giọng, style, tên quốc gia và nguyên tắc không có trẻ em. Không chạy nguyên script tập 6 cho tập khác.
'''
(H/prefix/'PRODUCTION_STEPS_APPLIED.md').write_text(steps)
readme=(R/'package/README.md').read_text().replace('Bộ này được bàn giao trước khi tạo voice; thời lượng âm thanh thực phải được đo sau render.','Tài liệu đã được bàn giao trước voice; nay đã có 17 MP3 được kiểm tra đúng 21:00 sau giải mã.').replace('17voice riêng sẽ giữ đúng mã giọng và nhấn nhá đã lưu','17voice riêng đã giữ đúng mã giọng và nhấn nhá đã lưu');readme+='\n\nĐã hoàn tất 17 voice, mỗi bản đã kiểm tra 21:00 sau giải mã. [Tải từng voice](VOICES/DOWNLOAD_LINKS.md) · [Quy trình đã lưu](PRODUCTION_STEPS_APPLIED.md) · [QA âm thanh](VOICES/VOICE_RELEASE_QA.json). ZIP tài liệu bàn giao trước voice được giữ bất biến. Bản dịch/nghe và phương ngữ H’Mông Trắng còn cần người bản ngữ rà soát độc lập. Chưa dựng video tập 6.\n';(H/prefix/'README.md').write_text(readme)
workflow_state=json.load(open(R/'VOICE_WORKFLOW_STATE.json'));final_run=workflow_state['delivery_workflow_run_id'];s=json.load(open(R/'SERIES_STATE.documents.json'));before=json.load(open(R/'SERIES_STATE.before.json'));done=s.pop('in_progress_topic_6');done.update(voice_status='17_expressive_voices_delivered_technical_qa_passed_native_review_pending',voice_files_delivered=17,verified_seconds_per_voice=1260,voice_release_tag=release['tag_name'],voice_release_url=release['html_url'],voice_release_published_at=release['published_at'],voice_archive_url=assets['DENISOVA_06_17_VOICES_TEN_QUOC_GIA.zip']['browser_download_url'],voice_archive_sha256=assets['DENISOVA_06_17_VOICES_TEN_QUOC_GIA.zip']['digest'].split(':')[1],voice_details_url=assets['DENISOVA_06_HO_SO_GIONG_TEN_QUOC_GIA.zip']['browser_download_url'],voice_asset_digests_verified=True,voice_country_names_delivered=True,voice_workflow_run_id=final_run,voice_workflow_url=f'https://github.com/seotro95/seotro/actions/runs/{final_run}',voice_workflow_run_ids=[42791520378,final_run],voice_build_branch='codex/denisova-voice-build-20261110',translation_native_review_pending=True,white_hmong_dialect_independently_verified=False,verified_voice_locales=list(by),english_voice_sha256=by['en-US']['sha256'],native_hmong_sha256=by['mww']['sha256'],native_hmong_reference_sha256='ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17',main_video_audio_language='en-US',production_steps_document=str(prefix/'PRODUCTION_STEPS_APPLIED.md'),voice_generation_source_path=str(prefix/'VOICES/PRODUCTION_SCRIPTS'),video_status='awaiting_episode6_generated_clips')
s['completed_topic_6']=done;s['active_topic']=None;s['next_topic_id']=5;s['last_requested_topic_id']=6;s['topic5_explicitly_left_queued']=True
for k in ['completed_topic_1','completed_topic_2','completed_topic_3','completed_topic_4']:assert s[k]==before[k]
for key in ['topics','next_topics']:
 for item in s.get(key,[]):
  if item.get('id')==6:item.update(status='documents_and_17_expressive_voices_delivered_video_pending_native_review_pending',created=True)
  if item.get('id')==5:assert item['status']=='queued'
series=H/'productions/series';series.mkdir(parents=True,exist_ok=True);(series/'SERIES_STATE.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n');shutil.copy(R/'PRODUCTION_DEFAULTS.documents.json',series/'PRODUCTION_DEFAULTS.json')
for n in ['VOICE_PROFILES_LOCKED.json','NARRATION_STYLE_LOCKED.json','VOICE_FILE_NAMING.json']:shutil.copy(D/n,series/n)
bookmark='''# Tiếp tục từ đây — chủ đề 6 đã bàn giao tài liệu và 17 voice

Denisova: 21:00, 3425 từ Anh, 126 ô 10 giây, 110 prompt mới/11 TXT và 16 ô REUSE. [Tải voice](video-06-denisova/VOICES/DOWNLOAD_LINKS.md) · [Quy trình](video-06-denisova/PRODUCTION_STEPS_APPLIED.md).

Giữ 16 giọng nam và H’Mông trắng nữ 3 đúng ID/mẫu/style đã khóa, tên file theo quốc gia. Không có hình trẻ em. Voice đã qua QA kỹ thuật; bản dịch/nghe/phương ngữ còn cần rà soát bản ngữ độc lập. Video tập 6 chờ clip của chính tập này; khi có, chỉ dùng voice Anh, bỏ âm thanh clip và mở đầu 12 shot/30 giây trong tổng 21 phút.

Tập 1–4 đã bàn giao video, không tạo lại. Tập 5 vẫn queued vì người dùng chọn làm tập 6 trước. Chưa bắt đầu tập 7; không tự bắt đầu tập khác. Đọc SERIES_STATE và PRODUCTION_DEFAULTS trước khi làm tiếp. Mặc định chuỗi vẫn 20 phút; 21 phút là ngoại lệ riêng tập 6.

---

'''+(R/'BOOKMARK.before.md').read_text();(H/'productions/TIEP_TUC_TU_DAY.md').write_text(bookmark)
entries=[{'path':str(p.relative_to(H)),'mode':'100644','type':'blob','content':p.read_text()} for p in sorted(H.rglob('*')) if p.is_file()]
groups=[];group=[];size=0
for e in entries:
 n=len(json.dumps(e,ensure_ascii=False).encode())
 if group and size+n>360000:groups.append(group);group=[];size=0
 group.append(e);size+=n
if group:groups.append(group)
for i,g in enumerate(groups):(R/f'voice-handoff-group-{i}.json').write_text(json.dumps(g,ensure_ascii=False))
(R/'VOICE_HANDOFF_STAGING.json').write_text(json.dumps({'groups':len(groups),'files':len(entries),'characters':[len(json.dumps(g,ensure_ascii=False)) for g in groups]},indent=2));print((R/'VOICE_HANDOFF_STAGING.json').read_text())
