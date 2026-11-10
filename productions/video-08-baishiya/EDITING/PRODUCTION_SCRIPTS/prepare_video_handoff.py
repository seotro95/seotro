import json,shutil
from pathlib import Path
R=Path(__file__).parent;H=R/'github-handoff';prefix=Path('productions/video-08-baishiya');P=H/prefix/'EDITING';P.mkdir(parents=True,exist_ok=True)
q=json.loads((R/'delivery/FINAL_VIDEO_QA.json').read_text());v=json.loads((R/'PUBLIC_RELEASE_VERIFICATION.json').read_text())
assert q['status']==v['status']=='passed' and q['final_visual_review']['status']=='passed'
assets={x['name']:x for x in v['assets']};state=json.loads((R/'EDIT_WORKFLOW_STATE.json').read_text())
release='baishiya-video-08-final-22m20s';base='https://github.com/seotro95/seotro/releases/download/'+release+'/'
for p in (R/'delivery').iterdir():
    if p.suffix in ['.txt','.md','.csv','.srt','.json']:shutil.copyfile(p,P/p.name)
for n in ['PUBLIC_RELEASE_VERIFICATION.json','PUBLICATION_DESTINATION_PROOF.json','PUBLICATION_PRIVACY_SCAN.json','EDIT_PLAN.json','SCENE_VERIFICATION.json','VISUAL_REVIEW_APPROVED.json','RENDER_INTERMEDIATE_CLEANUP.json']:
    shutil.copyfile(R/n,P/n)
D=P/'PRODUCTION_SCRIPTS';D.mkdir(exist_ok=True)
for n in ['build_plan.py','link_sources.py','render_edit.py','assemble_final.py','qa_final.py','review_final.py','package_delivery.py','prepare_final_transfer.py','verify_public_release.py','prepare_video_handoff.py']:
    shutil.copyfile(R/n,D/n)
shutil.copyfile(R/'EDIT_WORKFLOW_STATE.json',D/'EDIT_WORKFLOW_STATE.json')
s=json.loads((R/'SERIES_STATE.edit_base.json').read_text());old=json.loads(json.dumps(s));t=s['completed_topic_8']
t.update(video_rendered=True,video_status='final_english_video_qa_passed_and_published',video_release_tag=release,
         video_url=assets['BAISHIYA_08_EN_FINAL_22m20s_720p.mp4']['url'],video_duration_seconds=1340,
         video_width=1280,video_height=720,video_fps=24,video_sha256=q['sha256'],video_bytes=q['bytes'],
         video_audio_streams=1,video_audio_language='English',video_source_audio_removed=True,video_music_added=False,
         video_opening_shots=12,video_planned_shots=q['planned_shots'],video_source_upload_count=114,
         video_unique_uploaded_clips=114,video_exact_duplicates=0,video_unique_source_clips_used=q['unique_source_clips_used'],
         video_science_graphic_count=q['science_graphic_count'],video_no_children_policy=True,
         video_english_voice_sha256=q['reference_voice_sha256'],video_main_voice_narration_style_id='science-documentary-expressive-v1',
         video_edit_project_url=assets['BAISHIYA_08_EDIT_PROJECT.zip']['url'],video_qa_url=assets['FINAL_VIDEO_QA.json']['url'],
         video_publish_workflow_run_id=state['publish_run_id'],video_release_published_at=v['published_at'],
         video_download_verified=True,video_render_location='local',video_raw_source_clips_in_delivery=False,
         video_titles_thumbnail_txt_url=assets['BAISHIYA_08_TITLES_THUMBNAILS.txt']['url'],
         video_titles_thumbnail_zip_url=assets['BAISHIYA_08_TITLES_THUMBNAILS.zip']['url'],
         video_visual_review_scope=q['final_visual_review']['scope'],
         video_original_uploads_preserved=True,video_local_download_caches_evicted=True)
for key in ['topics','next_topics']:
    for x in s.get(key,[]):
        if x.get('id')==8:x['status']='video_and_17_expressive_voices_delivered_native_review_pending'
s['active_topic']=None;s['last_requested_topic_id']=8
for i in [1,2,3,4,6]:assert s[f'completed_topic_{i}']==old[f'completed_topic_{i}']
assert s['next_topic_id']==old['next_topic_id']==5
for x in s['topics']:
    if x['id'] in [5,7,9]:assert x['status']=='queued'
series=H/'productions/series';series.mkdir(parents=True,exist_ok=True)
(series/'SERIES_STATE.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
bookmark=f'''# Chủ đề 8 Baishiya đã hoàn tất video và 17 voice

[Video Anh 22:20]({base}BAISHIYA_08_EN_FINAL_22m20s_720p.mp4) · [Mở đầu 30 giây]({base}BAISHIYA_08_OPENING_30s.mp4) · [Dự án]({base}BAISHIYA_08_EDIT_PROJECT.zip) · [5 tiêu đề và 5 prompt thumbnail TXT]({base}BAISHIYA_08_TITLES_THUMBNAILS.txt) · [ZIP dự phòng]({base}BAISHIYA_08_TITLES_THUMBNAILS.zip).

Video 1280×720/24 fps, 32.160 khung hình, chỉ voice Anh đã khóa. Không tiếng clip, nhạc hoặc SFX. 12 cảnh mở đầu trong 30 giây, tổng 22:20, 275 shot và 7 chuyển cảnh hòa hình ngắn. Đã đối chiếu 114 clip, chọn 91 clip cùng 19 đồ họa. Sáu mã prompt thiếu được giải quyết bằng cảnh cùng nội dung và đồ họa phù hợp. Không hình trẻ em trong các mẫu cảnh đã chọn.

Voice Anh SHA256 14131b625739f903c4f165a02ffc60c5d54b9f09dd628cf92a13f64477e222c4; giữ nguyên lời, nhịp và cao độ. 17 voice đã bàn giao được giữ nguyên ID, mẫu, style và tên quốc gia. Bản dịch/nghe và phương ngữ H’Mông Trắng vẫn cần người bản ngữ rà soát độc lập.

Chỉ phát hành bản dựng và tài liệu. Không kèm clip gốc, proxy hoặc ảnh contact từ nguồn. Các bản tải lên Sediment vẫn nguyên vẹn; chỉ bộ nhớ đệm tải về và scene dựng đã ghép được thu hồi để tiết kiệm dung lượng. Tệp nguồn được đối chiếu mã băm trước khi dựng. Project có script link_sources.py để dùng lại bản gốc người dùng giữ.

Giới hạn bằng chứng được giữ: tuổi tối thiểu của hàm, tuổi lớp chứa Xiahe 2, nguồn gốc vết đốt chưa rõ, không khẳng định cư trú liên tục hoặc bộ gene Xiahe hoàn chỉnh. Đồ họa có chú thích; bản đồ chỉ định hướng địa lý hiện đại.

Đã kiểm toàn bộ giải mã, thời lượng, một đường tiếng Anh, 12 chương, 134 cue phụ đề và 15 điểm đồng bộ âm thanh. Rà mẫu bản dựng mở đầu, chương, đồ họa và kết; không tuyên bố xem tay liên tục cả phim. Xem [hồ sơ dựng](video-08-baishiya/EDITING/README.md) và SERIES_STATE.

Giữ kết quả tập 1–4 và 6; tập 5 và 7 vẫn queued. Không tự bắt đầu 9 hoặc tạo lại voice đã chốt. Mặc định chuỗi vẫn 20 phút; 22:20 là ngoại lệ riêng tập 8.

---

Nhật ký trước đó; trạng thái hiện tại nằm ở đầu trang.

'''+(R/'BOOKMARK.edit_base.md').read_text()
(H/'productions/TIEP_TUC_TU_DAY.md').write_text(bookmark)
readme=(R/'EPISODE_README.edit_base.md').read_text().replace('Chưa cóclip8,chưa dựngvideo8.','Video 8 đã dựng xong và kiểm tra; xem liên kết dưới đây.')
readme+=f'\n\n## Video hoàn chỉnh\n\n[Tải video 22:20]({base}BAISHIYA_08_EN_FINAL_22m20s_720p.mp4) · [Mở đầu 30 giây]({base}BAISHIYA_08_OPENING_30s.mp4) · [Project]({base}BAISHIYA_08_EDIT_PROJECT.zip) · [5 tiêu đề và 5 prompt thumbnail TXT]({base}BAISHIYA_08_TITLES_THUMBNAILS.txt) · [ZIP dự phòng]({base}BAISHIYA_08_TITLES_THUMBNAILS.zip). Chỉ voice Anh gốc, bỏ mọi tiếng clip; mở đầu 12 cảnh/30 giây trong tổng 22:20. [Hồ sơ và QA](EDITING/README.md). Các bản tải lên nguồn giữ nguyên; không kèm footage gốc trong bản tải.\n'
(H/prefix/'README.md').write_text(readme)
steps=(R/'PRODUCTION_STEPS.edit_base.md').read_text().replace('Chưa dựng video8 vì chưa có clip của tập này. Khi nhận clip:','Video 8 đã dựng xong theo phần cập nhật dưới đây. Nguyên tắc áp dụng:')
steps+='''

## Cập nhật dựng video chủ đề 8

13. Nhận 114 clip mới 622–735, kiểm SHA256/stream và lấy mẫu đầu, giữa, gần cuối. 35 clip có tiếng gốc. Không công khai raw footage hoặc ảnh contact từ nguồn. Sáu mã BS08_002,014,027,072,075,116 thiếu được thay bằng cảnh phù hợp/đồ họa.
14. Chọn 91 clip. Loại toàn bộ cảnh có logo/chữ phát sinh, trang phục hoặc vật chứng dễ gây nhầm, người nền không rõ tuổi; không cắt watermark để tái sử dụng. Chỉ lấy chi tiết thân/chân ở hai clip động vật có sừng không khớp. Các mô hình hàm/dấu vết được ghi rõ là mẫu giảng giải.
15. Dựng 275 shot trong 134 ô 10 giây, 12 shot/30 giây đầu và 7 dissolve ngắn. 19 đồ họa gốc giải thích mốc tuổi, ZooMS, tài nguyên, giới hạn bằng chứng và EPAS1. Bản đồ hiện đại không có tuyến di cư khẳng định.
16. Tải lại nguồn riêng tư theo nhu cầu và xác minh hash; thu hồi chỉ cache cục bộ để tránh đầy đĩa. Các bản tải lên chuẩn vẫn nguyên vẹn. Render loại mọi audio clip bằng -an và map hình; ghép cuối chỉ map voice Anh đã khóa. Không retime hoặc đổi cao độ voice khi dựng; chỉ chuẩn hóa độ lớn.
17. Kiểm 32.160 frame/1.340 giây, 1 audio Anh, 12 chương, 134 cue/3.162 từ Anh, giải mã toàn bộ, khoảng đen, độ lớn/true peak và 15 điểm đồng bộ sóng âm. Rà mẫu mở đầu, chuyển chương, đồ họa và kết; ghi rõ phạm vi kiểm hình.
18. Tạo project không footage gốc, 5 cặp tiêu đề/prompt thumbnail trong TXT UTF-8 BOM và ZIP dự phòng. Dùng workflow riêng baishiya-final08.yml trên nhánh chuyển chỉ sản phẩm cuối; không ghi đè workflow tập cũ. Đối chiếu hash toàn bộ asset và tải kiểm đầy đủ MP4 công khai, rồi cập nhật trạng thái chuỗi. Giữ 17 voice và mọi tập trước; không tự bắt đầu tập mới.
'''
(H/prefix/'PRODUCTION_STEPS_APPLIED.md').write_text(steps)
entries=[{'path':str(p.relative_to(H)),'mode':'100644','type':'blob','content':p.read_text(encoding='utf-8')} for p in sorted(H.rglob('*')) if p.is_file()]
import re
for entry in entries:assert not re.search(r'file_[0-9a-f]{32}|/workspace/attachments/[0-9a-f]{8}-',entry['content']),entry['path']
groups=[];cur=[];size=0
for entry in entries:
    count=len(json.dumps(entry,ensure_ascii=False).encode())
    if cur and size+count>340000:groups.append(cur);cur=[];size=0
    cur.append(entry);size+=count
if cur:groups.append(cur)
for i,group in enumerate(groups):(R/f'final-git-group-{i}.json').write_text(json.dumps(group,ensure_ascii=False))
(R/'FINAL_GIT_STAGING.json').write_text(json.dumps({'groups':len(groups),'files':len(entries),'characters':[len(json.dumps(g,ensure_ascii=False)) for g in groups]},indent=2))
print((R/'FINAL_GIT_STAGING.json').read_text())
