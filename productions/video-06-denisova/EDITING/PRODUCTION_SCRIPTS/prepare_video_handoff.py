import json,shutil
from pathlib import Path
R=Path(__file__).parent;H=R/'github-handoff';prefix=Path('productions/video-06-denisova');P=H/prefix/'EDITING';P.mkdir(parents=True,exist_ok=True)
q=json.load(open(R/'delivery/FINAL_VIDEO_QA.json'));v=json.load(open(R/'PUBLIC_RELEASE_VERIFICATION.json'));assert q['status']==v['status']=='passed' and q['final_visual_review']['status']=='passed';assets={x['name']:x for x in v['assets']};release='denisova-video-06-final-21min';base='https://github.com/seotro95/seotro/releases/download/'+release+'/'
for p in (R/'delivery').iterdir():
 if p.suffix in ['.txt','.md','.csv','.srt','.json']:shutil.copy(p,P/p.name)
for n in ['PUBLIC_RELEASE_VERIFICATION.json','EDIT_PLAN.json','SCENE_VERIFICATION.json','VISUAL_REVIEW_APPROVED.json','RENDER_INTERMEDIATE_CLEANUP.json']:shutil.copy(R/n,P/n)
D=P/'PRODUCTION_SCRIPTS';D.mkdir(exist_ok=True)
for n in ['inventory.py','build_plan.py','render_edit.py','assemble_final.py','qa_final.py','review_final.py','package_delivery.py','prepare_final_transfer.py','verify_public_release.py','prepare_video_handoff.py','finish_local_pipeline.py']:shutil.copy(R/n,D/n)
shutil.copy(R/'EDIT_WORKFLOW_STATE.json',D/'EDIT_WORKFLOW_STATE.json')
s=json.load(open(R/'SERIES_STATE.edit_base.json'));old=json.loads(json.dumps(s));state=json.load(open(R/'EDIT_WORKFLOW_STATE.json'));t=s['completed_topic_6'];t.update(video_rendered=True,video_status='final_english_video_qa_passed_and_published',video_release_tag=release,video_url=assets['DENISOVA_06_EN_FINAL_21m_720p.mp4']['url'],video_duration_seconds=1260,video_width=1280,video_height=720,video_fps=24,video_sha256=q['sha256'],video_bytes=q['bytes'],video_audio_streams=1,video_audio_language='English',video_source_audio_removed=True,video_music_added=False,video_opening_shots=12,video_planned_shots=224,video_source_upload_count=104,video_unique_uploaded_clips=104,video_exact_duplicates=0,video_unique_source_clips_used=q['unique_source_clips_used'],video_science_graphic_count=30,video_no_children_policy=True,video_english_voice_sha256='d733faf7cb437ff9db733a7f5f9f527aa177a3e688abdd270f313af2ab3605ad',video_main_voice_narration_style_id='science-documentary-expressive-v1',video_edit_project_url=assets['DENISOVA_06_EDIT_PROJECT.zip']['url'],video_qa_url=assets['FINAL_VIDEO_QA.json']['url'],video_publish_workflow_run_id=state['publish_run_id'],video_release_published_at=v['published_at'],video_download_verified=True,video_render_location='local',video_raw_source_clips_in_delivery=False,video_titles_thumbnail_txt_url=assets['DENISOVA_06_TITLES_THUMBNAILS.txt']['url'],video_titles_thumbnail_zip_url=assets['DENISOVA_06_TITLES_THUMBNAILS.zip']['url'],video_visual_review_scope='104 sources sampled at3times and44final frames reviewed; not continuous manual viewing.')
for key in ['topics','next_topics']:
 for x in s.get(key,[]):
  if x.get('id')==6:x['status']='video_and_17_expressive_voices_delivered_native_review_pending'
s['active_topic']=None;s['next_topic_id']=5;s['last_requested_topic_id']=6;s['topic5_explicitly_left_queued']=True
for i in [1,2,3,4]:assert s[f'completed_topic_{i}']==old[f'completed_topic_{i}']
for k in ['topics','next_topics']:
 for x in s.get(k,[]):
  if x.get('id')==5:assert x['status']=='queued'
series=H/'productions/series';series.mkdir(parents=True,exist_ok=True);(series/'SERIES_STATE.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
oldbookmark=(R/'BOOKMARK.edit_base.md').read_text();oldbookmark=oldbookmark.replace('Video tập 6 chờ clip của chính tập này; khi có, chỉ dùng voice Anh, bỏ âm thanh clip và mở đầu 12 shot/30 giây trong tổng 21 phút.','Video tập 6 đã dựng xong theo voice Anh, bỏ âm thanh clip và mở đầu 12 shot/30 giây trong tổng 21 phút.')
bookmark=f'''# Chủ đề 6 Denisova đã hoàn tất video và 17 voice

[Video Anh21:00]({base}DENISOVA_06_EN_FINAL_21m_720p.mp4) · [Mở đầu30s]({base}DENISOVA_06_OPENING_30s.mp4) · [Dự án]({base}DENISOVA_06_EDIT_PROJECT.zip) · [5tiêu đề/thumbnail TXT]({base}DENISOVA_06_TITLES_THUMBNAILS.txt) · [ZIP dự phòng]({base}DENISOVA_06_TITLES_THUMBNAILS.zip).

Video1280×720/24fps, chỉ voiceAnh đã khóa, không tiếngclip/nhạc/SFX. 12shot mở đầu30s, tổng21:00,224shot và9dissolve; đã kiểm toàn bộ30240frame,15điểm đồng bộ và44khung hình cuối.104clip được đối chiếu, chọn63clip cùng30đồ họa. Chỉ người trưởng thành trong cảnh đã chọn; không dựng chủ mẫu trẻ. Sáu ô thiếu clip được xử lý bằng bản đồ và cảnh phù hợp.

17voice riêng giữ nguyên ID/style/tên quốc gia; bản dịch/nghe và phương ngữH’MôngTrắng còn cần rà soát bản ngữ. Không tạo lại tập1–4 hoặc tập6. Tập5 vẫn queued vì người dùng chọn6 trước; chưa bắt đầu7, không tự làm tập khác.

Dựng tại phiên, giữ mọi clip gốc. Chỉ công bố bản dựng và tài liệu; không kèm video nguồn trong project hay nhánh công khai. Việc tạo nhánh công khai104clip gốc đã bị duyệt tự động từ chối, nên không tiếp tục cách đó. Các file trung gian dựng được xóa sau khi ghép để tiết kiệm dung lượng; có thể tái tạo từ nguồn cục bộ và project. Không xóa clip người dùng đã gửi.

Đọc [hồ sơ dựng](video-06-denisova/EDITING/README.md), trạng thái chuỗi và cấu hình trước khi làm tiếp.

---

Nhật ký bàn giao trước đó; trạng thái hiện tại nằm ở đầu trang.

'''+oldbookmark
(H/'productions/TIEP_TUC_TU_DAY.md').write_text(bookmark)
readme=(R/'EPISODE_README.edit_base.md').read_text().replace('Chưa dựng video tập 6.','Đã dựng xong video tập 6; xem liên kết dưới đây.');readme+=f'\n\n## Video hoàn chỉnh\n\n[Tải video21:00]({base}DENISOVA_06_EN_FINAL_21m_720p.mp4) · [Mở đầu30s]({base}DENISOVA_06_OPENING_30s.mp4) · [Project]({base}DENISOVA_06_EDIT_PROJECT.zip) · [5tiêu đề và5promptthumbnail TXT]({base}DENISOVA_06_TITLES_THUMBNAILS.txt) · [ZIP dự phòng cho TXT]({base}DENISOVA_06_TITLES_THUMBNAILS.zip). Chỉ voiceAnh gốc, bỏmọitiếngclip; mở đầu12shot/30s trong21phút. [Hồ sơ và QA](EDITING/README.md). Clip gốc được giữ tại phiên, không kèm trong bản tải.\n';(H/prefix/'README.md').write_text(readme)
steps=(R/'PRODUCTION_STEPS.edit_base.md').read_text().replace('Chưa dựng video tập 6 vì chưa có clip của tập này.','Video tập 6 nay đã dựng xong; xem phần cập nhật dưới đây.')
steps+='''\n\n## Cập nhật dựng video chủ đề6\n\n1. Nhận104clip518–621, kiểmSHA256/metadata và lấy mẫu0,8/4,9/9,1giây. Tất cả10giây,720p24fps;33clip có tiếng. Đối chiếu với110prompt, xử lý6ô thiếu bằng bản đồ và cảnh phù hợp.\n2. Chọn63clip phù hợp, thay bản đồ và dữ liệu doAIvẽ lại bằng30đồ họa có chú thích; bỏclip025 đổi danh tính chủ thể. Không có hình trẻ em trong cảnh được chọn qua kiểm tra mẫu.\n3. Dựng224shot trong126ô10giây, mở đầu12shot/30s và9dissolve ngắn nằm trong tổng21:00. Chữ mở đầu nhấn vật chứng/năm2010/Denisovans.\n4. Giữ nguyên voiceAnhSHA256d733faf7cb437ff9db733a7f5f9f527aa177a3e688abdd270f313af2ab3605ad. Bỏmọi tiếngclip bằng-mapvà-an; chỉ chuẩn hóa độ lớn khi xuất, không đổi nhịp hoặc cao độ.\n5. Dựng trực tiếp sau khi duyệt tự động từ chối công khai clip nguồn. Không tạo nhánh chứa video gốc; chỉ phát hành bản dựng và tài liệu. Giữ toàn bộ nguồn người dùng; giải phóng file dựng trung gian đã ghép với khoảng an toàn60giây để đủ chỗ.\n6. Kiểm30240frame,1260giây,1audioAnh,12chương,126cueSRT,3425từAnh,giải mãtoànbộ,không khoảng đen dài và15điểm đồng bộ sóng âm. Rà44khung hình từbản cuối; không tuyên bố xem tay liên tục21phút.\n7. Đưa chỉ sản phẩm hoàn chỉnh lênGitHubRelease, xác minhSHA256từngasset và tải kiểmtoànbộMP4côngkhai; tệpTXT/ZIP dùng linkAsset để tải trực tiếp. Lưu kế hoạch,code,báocáo,hồsơvàlinktrongEDITING. Giữ17voice đã bàn giao vàtập5queued.\n''';(H/prefix/'PRODUCTION_STEPS_APPLIED.md').write_text(steps)
entries=[{'path':str(p.relative_to(H)),'mode':'100644','type':'blob','content':p.read_text(encoding='utf-8')} for p in sorted(H.rglob('*')) if p.is_file()];groups=[];cur=[];size=0
for e in entries:
 n=len(json.dumps(e,ensure_ascii=False).encode())
 if cur and size+n>360000:groups.append(cur);cur=[];size=0
 cur.append(e);size+=n
if cur:groups.append(cur)
for i,g in enumerate(groups):(R/f'final-git-group-{i}.json').write_text(json.dumps(g,ensure_ascii=False))
(R/'FINAL_GIT_STAGING.json').write_text(json.dumps({'groups':len(groups),'files':len(entries),'characters':[len(json.dumps(g,ensure_ascii=False)) for g in groups]},indent=2));print((R/'FINAL_GIT_STAGING.json').read_text())
