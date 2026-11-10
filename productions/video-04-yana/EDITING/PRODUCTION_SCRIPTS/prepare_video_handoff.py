import json,shutil
from pathlib import Path
R=Path(__file__).parent;H=R/'github-handoff';P=H/'productions/video-04-yana/EDITING';P.mkdir(parents=True,exist_ok=True)
q=json.loads((R/'delivery/FINAL_VIDEO_QA.json').read_text());v=json.loads((R/'PUBLIC_RELEASE_VERIFICATION.json').read_text());assert q['status']==v['status']=='passed'
assets={x['name']:x for x in v['assets']};release='yana-video-04-final-23min';base='https://github.com/seotro95/seotro/releases/download/'+release+'/'
for p in (R/'delivery').iterdir():
 if p.suffix in ['.txt','.md','.csv','.srt','.json']:shutil.copy(p,P/p.name)
shutil.copy(R/'PUBLIC_RELEASE_VERIFICATION.json',P/'PUBLIC_RELEASE_VERIFICATION.json');shutil.copy(R/'EDIT_PLAN.json',P/'EDIT_PLAN.json');shutil.copy(R/'SCENE_VERIFICATION.json',P/'SCENE_VERIFICATION.json')
D=P/'PRODUCTION_SCRIPTS';D.mkdir(exist_ok=True)
for name in ['inventory.py','build_plan.py','render_edit.py','assemble_final.py','qa_final.py','review_final.py','package_delivery.py','prepare_transfer.py','verify_public_release.py','prepare_video_handoff.py']:shutil.copy(R/name,D/name)
shutil.copy(R/'EDIT_WORKFLOW_STATE.json',D/'EDIT_WORKFLOW_STATE.json')
s=json.loads((R/'SERIES_STATE.edit_base.json').read_text());old=json.loads(json.dumps(s));t=s['completed_topic_4'];t.update(video_rendered=True,video_status='final_english_video_qa_passed_and_published',video_release_tag=release,video_url=assets['YANA_04_EN_FINAL_23m_720p.mp4']['url'],video_duration_seconds=1380,video_width=1280,video_height=720,video_fps=24,video_sha256=q['sha256'],video_bytes=q['bytes'],video_audio_streams=1,video_audio_language='English',video_source_audio_removed=True,video_music_added=False,video_opening_shots=12,video_source_upload_count=133,video_unique_uploaded_clips=115,video_exact_duplicates=18,video_unique_source_clips_used=q['unique_source_clips_used'],video_science_graphic_count=22,video_no_children_policy=True,video_english_voice_sha256='7014702fdb86744e8ddbf8a74eb7ef176bbb4cb9865aaf4e0e7931e27ae0047c',video_main_voice_narration_style_id='science-documentary-expressive-v1',video_edit_project_url=assets['YANA_04_EDIT_PROJECT.zip']['url'],video_qa_url=assets['FINAL_VIDEO_QA.json']['url'],video_publish_workflow_run_id=json.loads((R/'EDIT_WORKFLOW_STATE.json').read_text())['publish_run_id'],video_release_published_at=v['published_at'],video_download_verified=True)
for key in ['topics','next_topics']:
 for x in s.get(key,[]):
  if x.get('id')==4:x['status']='video_and_17_expressive_voices_delivered_native_review_pending'
s['active_topic']=None;s['next_topic_id']=5
for i in [1,2,3]:assert s[f'completed_topic_{i}']==old[f'completed_topic_{i}']
series=H/'productions/series';series.mkdir(parents=True,exist_ok=True);(series/'SERIES_STATE.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
bookmark=(R/'BOOKMARK.edit_base.md').read_text();bookmark=bookmark.replace('Chờcliptập4 để dựng; chủ đề tiếp theo5—UpwardSunRiver, chưa bắt đầu.',f'Đã bàn giao [videoAnh23:00]({base}YANA_04_EN_FINAL_23m_720p.mp4), mở đầu12shot/30s, chỉ voiceAnh và bỏmọitiếngclip. Chủ đề tiếp theo5—UpwardSunRiver, chưa bắt đầu.')
bookmark=bookmark.replace('Chưa cóvideohoànchỉnhtập4.','Đã có video hoàn chỉnh tập4.').replace('Nếu người dùng gửiclipYana, dựngtập4 theo voiceAnh đã khóa trước khi chuyển việc khác.','Tập4 đã dựng xong theo voiceAnh đã khóa.').replace('Giữ17ID,nhấn nhá và tên quốc gia đã khóa.','Giữ17ID,nhấn nhá và tên quốc gia đã khóa. Video tập4 đã xong23:00,1280×720/24fps,12shot mở đầu30s; xem EDITING/README.md.')
bookmark+='\n\n## Bàn giao video chủ đề4\n\nĐã dựng và xuất bản23:00, chỉ voiceAnh gốc có nhấn nhá.133upload/115clipkhácnhau/18bảntrùng; chọn cảnh người trưởng thành, bỏ mọi tiếngclip và cảnh không phù hợp.12shot trong30giây đầu; các chương theo ranh120/110s. [Video]('+base+'YANA_04_EN_FINAL_23m_720p.mp4) · [Project]('+base+'YANA_04_EDIT_PROJECT.zip) · [5tiêu đề/thumbnail]('+base+'TITLES_AND_THUMBNAIL_PROMPTS.txt). Tập5 vẫn chưa bắt đầu.\n'
(H/'productions/TIEP_TUC_TU_DAY.md').write_text(bookmark)
readme=(R/'EPISODE_README.edit_base.md').read_text();readme=readme.replace('Chưa dựng video tập4 vì chưa có clip của tập này.','Đã dựng xong video tập4; xem liên kết bên dưới.');readme+='\n\n## Video hoàn chỉnh\n\n[Tải video23:00]('+base+'YANA_04_EN_FINAL_23m_720p.mp4) · [Mở đầu30s]('+base+'YANA_04_OPENING_30s.mp4) · [Project]('+base+'YANA_04_EDIT_PROJECT.zip) · [5tiêu đề và5promptthumbnail]('+base+'TITLES_AND_THUMBNAIL_PROMPTS.txt). Chỉ voiceAnh gốc; đã loại tiếngclip.12shot/30s, không thêm intro. Không có hình trẻ em trong cảnh được chọn. [Hồ sơ dựng và kiểm tra](EDITING/README.md).\n';(H/'productions/video-04-yana/README.md').write_text(readme)
entries=[{'path':str(p.relative_to(H)),'mode':'100644','type':'blob','content':p.read_text()} for p in sorted(H.rglob('*')) if p.is_file()];groups=[];cur=[];size=0
for e in entries:
 n=len(json.dumps(e,ensure_ascii=False).encode())
 if cur and size+n>360000:groups.append(cur);cur=[];size=0
 cur.append(e);size+=n
if cur:groups.append(cur)
for i,g in enumerate(groups):(R/f'final-git-group-{i}.json').write_text(json.dumps(g,ensure_ascii=False))
(R/'FINAL_GIT_STAGING.json').write_text(json.dumps({'groups':len(groups),'files':len(entries),'characters':[len(json.dumps(g,ensure_ascii=False)) for g in groups]},indent=2));print((R/'FINAL_GIT_STAGING.json').read_text())
