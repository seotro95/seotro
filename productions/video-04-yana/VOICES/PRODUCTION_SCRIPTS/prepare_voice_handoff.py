import json,shutil
from pathlib import Path
R=Path(__file__).parent;D=R/'verified-release/details';H=R/'final-handoff';H.mkdir(exist_ok=True)
qa=json.loads((R/'VOICE_RELEASE_QA.json').read_text());assert qa['status']=='passed'
release=json.loads((R/'RELEASE_METADATA.json').read_text());assets={x['name']:x for x in release['assets']}
prefix=Path('productions/video-04-yana');V=H/prefix/'VOICES';V.mkdir(parents=True,exist_ok=True)
for p in D.rglob('*'):
 if p.is_file():
  dest=V/p.relative_to(D);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,dest)
shutil.copy(R/'VOICE_RELEASE_QA.json',V/'VOICE_RELEASE_QA.json')
shutil.copy(R/'VOICE_INPUT_QA.json',V/'VOICE_INPUT_QA.json')
shutil.copy(R/'HMONG_INPUT_VALIDATION.json',V/'HMONG_INPUT_VALIDATION.json')
M=json.loads((D/'AUDIO_MANIFEST.json').read_text());by={x['locale']:x for x in M['voices']}
base='https://github.com/seotro95/seotro/releases/download/yana-video-04-23min/'
linkdoc='# Tải voice — chủ đề 4 Yana\n\nTất cả 17 MP3 dài 23:00. Video chính dùng bản Mỹ/tiếng Anh.\n\n| Quốc gia/ngôn ngữ | Giới tính | Tải MP3 |\n|---|---|---|\n'
for m in M['voices']:linkdoc+=f'| {m["name"]} | {m["gender"]} | [Tải]({base}{m["filename"]}) |\n'
linkdoc+=f'\n[ZIP đủ17voice]({base}YANA_04_17_VOICES_TEN_QUOC_GIA.zip) · [Hồ sơ giọng]({base}YANA_04_HO_SO_GIONG_TEN_QUOC_GIA.zip)\n\nĐã kiểm tra file, mã giọng, nhấn nhá và thời lượng. Bản dịch/nghe và phương ngữ H’Mông Trắng vẫn cần rà soát độc lập bởi người bản ngữ.\n'
(V/'DOWNLOAD_LINKS.md').write_text(linkdoc)
P=V/'PRODUCTION_SCRIPTS';P.mkdir(exist_ok=True)
names=['render_common.py','render_online.py','render_hmong.py','prosody.py','job_init.py','publish_voices_job.py','stage_native.py','make_workflow.py','prepare_scripts.py','repair_translation_sources.py','apply_vietnamese_review.py','apply_hmong_review.py','validate_voice_inputs.py','verify_release.py','prepare_voice_handoff.py','vietnamese_reviewed_chapters.txt','hmong_reviewed_chapters.txt','VOICE_WORKFLOW_STATE.json','DOCUMENT_DELIVERY_STATE.json','BASELINE_VOICE_PROFILES.json']
for n in names:shutil.copy(R/n,P/n)
shutil.copy(R/'github-build/input/source_integrity.json',P/'source_integrity.json')
shutil.copy(R/'github-build/.github/workflows/siberia-final-voices.yml',P/'GITHUB_ACTIONS_BUILD_WORKFLOW.yml')
for n in ['SCRIPTS_INPUT','REVIEW_MARKERS']:(P/n).mkdir(exist_ok=True)
for p in (R/'voice/scripts').iterdir():
 if p.is_file():shutil.copy(p,P/('SCRIPTS_INPUT' if p.suffix=='.json' else 'REVIEW_MARKERS')/p.name)
steps='''# Các bước đã áp dụng — chủ đề 4 Yana

1. Đọc trạng thái chuỗi và danh sách chủ đề đã lưu; chọn Yana, giữ nguyên các tập1–3 đã bàn giao.23phút là ngoại lệ riêng tập4.
2. Dùng đúng video nguồn đã đối chiếu SHA256; học nhịp mở đầu/cỡ cảnh/cắt cảnh, viết lời mới từ tài liệu khoa học. Không sao chép lời nguồn.
3. Viết3648từ tiếng Anh trong138ô10s, lập12chương theo ranh thật: sáu chương120s rồi sáu chương110s. Không áp dụng12x115s.
4. Lập120prompt độc lập10s trong12TXT,10prompt/TXT; đánh dấu18ôREUSE và clip nguồn trong timeline. Video tạo hoàn toàn im lặng.
5. Không tạo hình trẻ em ở bất kỳ vị trí nào. Con người trong prompt phải trưởng thành rõ25–60tuổi, kể cả người nền/bóng/phản chiếu/ảnh/màn hình. Không tái hiện chủ mẫu răng; các cảnh người lớn chỉ minh hoạ cộng đồng.
6. Phát hành bộ tài liệu trước voice; giữ ZIP tài liệu gốc bất biến. Nguồn/giới hạn suy luận và bản đồ tham chiếu lưu kèm. Bản đồ NPS~21ka không phải đường bờ31,6ka hay lộ trình di cư đã biết.
7. Dịch16ngôn ngữ từ cùng kịch bản, rà thuật ngữ di truyền/khảo cổ và số; sửa rõ nghĩa ở14locale, viết lại12chương Việt và12chươngH’Mông. Giữ nguyên ý và mốc thời gian; vẫn cần kiểm duyệt bản ngữ độc lập.
8. Kiểm tra138cueAnh/12chươngdịch và toàn bộ đầu vào; công cụ H’Mông gốc từ chối token chữ-số liền nhau. Tách chữ khỏi số trong speechtext, để chính bộ chuẩn hóa của tool chuyển số thành từ. Không xoá số, không thay engine. File JSON mww đã kiểm tra là nguồn chuẩn; text nguồn và script tái tạo đã sửa để giữ khoảng cách chữ-số.
9. Giữ17ID,16nam/H’Môngnữ3, mẫu tham chiếu và style nhấn nhá đã khóa.16voice qua backendMelo được ghim mã nguồn; H’Mông quaVITS+OpenVoiceV2 gốc. Nhịp/nghỉ/nhấn âm lượng nhẹ, giữ cao độ; không giả lập chế độ cảm xúc engine không có.
10. Chạy previewAnh30s rồi render đủ16locale trênGitHubActions; nativeH’Mông chạy riêng cóWAVcheckpoint. Chỉ tiếp tục phần thiếu khi process dừng; không tổng hợp lại phần đã đạt.
11. CănAnh theo138ô10s; bản dịch theo12chương. Thay đổi tốc độ giữ cao độ trong giới hạn, không cắt lời. Mọi bản được giải mã đủ66.240.000mẫu tại48kHz=1380s. Khớp chương/tổng không có nghĩa khớp từng từ giữa các thứ tiếng.
12. Đổi tên bằng sao chép nguyên byte theo quốc gia, kiểmSHA256; phát hành17MP3,ZIPtổng/hồ sơ và bản tài liệu gốc. Kiểmserverdigest từng tài sản, báo cáo17locale, fulltextAnh138cue và giải mã độc lập fileAnh công khai.
13. Lưu trạng thái, mã/phiên bản, script17locale, timing, hồ sơ, linktải và quy trình. Chỉ dựng video khi có clip tập4: video chính chỉ voiceAnh, bỏmọitiếngclip, mở đầu8shot/30s nằm trong23phút. Chưa tạo video tập4.

Không chạy các script nguyên trạng cho tập5: đường dẫn, tiền tố, sốcue, thời lượng và chương phải lấy từ tập mới. GiữVOICE_PROFILES, NARRATION_STYLE vàVOICE_FILE_NAMING của chuỗi. Chủ đề tiếp theo đã lưu là5—UpwardSunRiver; chưa bắt đầu.
'''
(H/prefix/'PRODUCTION_STEPS_APPLIED.md').write_text(steps)
readme=(R/'package/README.md').read_text().replace('Đây là bản bàn giao tài liệu trước khi tạo voice; thời lượng thực phải đo sau render.','Tài liệu đã bàn giao trước khi tạo voice. Nay đủ17MP3, mỗi bản đã kiểm tra23:00 sau giải mã; xem [voice và linktải](VOICES/DOWNLOAD_LINKS.md). ZIPtài liệu gốc được giữ bất biến.')
readme+='\n\n[Quy trình đã áp dụng](PRODUCTION_STEPS_APPLIED.md) · [QAvoice](VOICES/VOICE_RELEASE_QA.json). Bản dịch, nghe và phương ngữH’Mông Trắng vẫn cần người bản ngữ rà soát độc lập. Chưa dựng video tập4 vì chưa có clip của tập này.\n'
(H/prefix/'README.md').write_text(readme)
s=json.loads((R/'SERIES_STATE.documents.json').read_text());done=s.pop('in_progress_topic_4');done['documents_zip_sha256']=done['document_zip_sha256'];done.update(voice_status='17_expressive_voices_delivered_technical_qa_passed_native_review_pending',voice_files_delivered=17,verified_seconds_per_voice=1380,voice_release_tag=release['tag_name'],voice_release_url=release['html_url'],voice_release_published_at=release['published_at'],voice_archive_url=assets['YANA_04_17_VOICES_TEN_QUOC_GIA.zip']['browser_download_url'],voice_archive_sha256=assets['YANA_04_17_VOICES_TEN_QUOC_GIA.zip']['digest'].split(':')[1],voice_details_url=assets['YANA_04_HO_SO_GIONG_TEN_QUOC_GIA.zip']['browser_download_url'],voice_asset_digests_verified=True,voice_country_names_delivered=True,voice_workflow_run_id=42774390626,voice_workflow_url='https://github.com/seotro95/seotro/actions/runs/42774390626',voice_build_branch='codex/yana-voice-build-20261110',translation_native_review_pending=True,white_hmong_dialect_independently_verified=False,verified_voice_locales=list(by),english_voice_sha256=by['en-US']['sha256'],native_hmong_sha256=by['mww']['sha256'],native_hmong_reference_sha256='ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17',main_video_audio_language='en-US',production_steps_document=str(prefix/'PRODUCTION_STEPS_APPLIED.md'),voice_generation_source_path=str(prefix/'VOICES/PRODUCTION_SCRIPTS'),video_status='awaiting_episode4_generated_clips')
s['completed_topic_4']=done;s['active_topic']=None;s['next_topic_id']=5
for key in ['topics','next_topics']:
 for item in s.get(key,[]):
  if item.get('id')==4:item.update(status='documents_and_17_expressive_voices_delivered_video_pending_native_review_pending',created=True)
series=H/'productions/series';series.mkdir(parents=True,exist_ok=True)
(series/'SERIES_STATE.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
shutil.copy(R/'PRODUCTION_DEFAULTS.documents.json',series/'PRODUCTION_DEFAULTS.json')
for n in ['VOICE_PROFILES_LOCKED.json','NARRATION_STYLE_LOCKED.json','VOICE_FILE_NAMING.json']:shutil.copy(D/n,series/n)
bookmark=(R/'BOOKMARK.documents.md').read_text()
bookmark=bookmark.replace('- Đang làm **chủ đề4—Yana,23:00** theo yêu cầu mới. Đã bàn giao kịch bản3648từ,120prompt/12TXT,18ôdùng lại và138mốc10s; đang chuẩn bị17voice. Không có hình trẻ em trong bất kỳ prompt nào. Không bắt đầu chủ đề5.','- Chủ đề4—Yana: đã bàn giao tài liệu23phút và17voice riêng có nhấn nhá, mỗi bản23:00; [linktải](video-04-yana/VOICES/DOWNLOAD_LINKS.md).120prompt/12TXT,18ôREUSE,138mốc10s. Không có hình trẻ em. Chờcliptập4 để dựng; chủ đề tiếp theo5—UpwardSunRiver, chưa bắt đầu.')
bookmark=bookmark.replace('22 phút là ngoại lệ riêng tập2.','22 phút là ngoại lệ riêng tập2,23phút riêng tập4.').replace('> Tiếp tục chủ đề4.','> Tiếp tục chủ đề5.').replace('Trạng thái tập3 đã hoàn tất tài liệu/voice, tiếp theo là tập4.','Đã hoàn tất tài liệu/voice tập4; tiếp theo5—UpwardSunRiver.').replace('## Lượt hiện tại — chủ đề4','## Chủ đề4 đã bàn giao tài liệu và17voice')
bookmark+='\n\nTập4 đã kiểm17serverdigest, đủthờilượng và fulltextAnh; hồ sơ ởVOICES, quy trìnhởPRODUCTION_STEPS_APPLIED.md. Chưa cóvideohoànchỉnhtập4. Nếu người dùng gửiclipYana, dựngtập4 theo voiceAnh đã khóa trước khi chuyển việc khác. Không tự bắt đầu tập5.\n'
(H/'productions/TIEP_TUC_TU_DAY.md').write_text(bookmark)
entries=[{'path':str(p.relative_to(H)),'mode':'100644','type':'blob','content':p.read_text()} for p in sorted(H.rglob('*')) if p.is_file()]
groups=[];group=[];size=0
for e in entries:
 n=len(json.dumps(e,ensure_ascii=False).encode())
 if group and size+n>370000:groups.append(group);group=[];size=0
 group.append(e);size+=n
if group:groups.append(group)
for i,g in enumerate(groups):(R/f'voice-handoff-group-{i}.json').write_text(json.dumps(g,ensure_ascii=False))
(R/'VOICE_HANDOFF_STAGING.json').write_text(json.dumps({'groups':len(groups),'files':len(entries),'characters':[len(json.dumps(g,ensure_ascii=False)) for g in groups]},indent=2))
print((R/'VOICE_HANDOFF_STAGING.json').read_text())
