import json,re,shutil
from pathlib import Path
R=Path(__file__).parent;O=R/'delivery';H=R/'github-handoff';P=H/'productions/video-19-kostenki';E=P/'EDITING';E.mkdir(parents=True,exist_ok=True)
v=json.loads((R/'PUBLIC_RELEASE_VERIFICATION.json').read_text());assert v['status']=='passed' and v['public_video_full_stream_sha256_verified']
q=json.loads((O/'FINAL_VIDEO_QA.json').read_text());assert q['status']=='passed'
assets={x['name']:x for x in v['assets']};main=assets['KOSTENKI_19_EN_FINAL_20m15s_720p.mp4'];assert main['sha256']==q['sha256']
for n in ['EDIT_PLAN.json','EDITOR_DECISIONS.json','SOURCE_MANIFEST.json','SUBSTITUTIONS.csv','VISUAL_REVIEW_APPROVED.json','SCENE_VERIFICATION.json','FINAL_EXPORT_COMMAND.json','PUBLIC_RELEASE_VERIFICATION.json','PUBLICATION_DESTINATION_PROOF.json','PUBLICATION_PRIVACY_SCAN.json','render_edit.py','assemble_final.py','qa_final.py','link_sources.py','package_delivery.py','prepare_video_handoff.py']:
 shutil.copyfile(R/n,E/n)
for n in ['FINAL_VIDEO_QA.json','RELEASE_ASSET_MANIFEST.json','KOSTENKI_19_TITLES_THUMBNAILS.txt','KOSTENKI_19_EN_SUBTITLES.srt','HUONG_DAN_DUNG_LAI.txt']:shutil.copyfile(O/n,E/n)
state=json.loads((R/'SERIES_STATE.edit_base.json').read_text());before=json.loads((R/'SERIES_STATE.edit_base.json').read_text());c=state['completed_topic_19']
c.update(video_status='completed_published_english_only20m15s',video_delivered=True,video_duration_seconds=1215,video_frames=29160,video_width=1280,video_height=720,video_fps=24,video_audio_language='en-US',video_audio_stream_count=1,video_publish_workflow_run_id=42951543679,video_release_tag=v['tag'],video_release_url=v['release_url'],video_download_url=main['url'],video_sha256=main['sha256'],video_bytes=main['bytes'],opening_shots=10,opening_seconds=30,source_audio_removed=True,music_added=False,replacement_stills_or_text_cards=0,video_qa_path='productions/video-19-kostenki/EDITING/FINAL_VIDEO_QA.json',public_video_stream_hash_verified=True,thumbnail_title_pairs=5,editing_steps_saved=True)
for t in state['topics']:
 if t['id']==19:t['status']='video_completed_english20m15s_documents_and17voices_delivered_native_review_pending'
for k in before:
 if k!='completed_topic_19' and k!='topics':assert state[k]==before[k]
for old,new in zip(before['topics'],state['topics']):
 if old['id']!=19:assert old==new
s=H/'productions/series';s.mkdir(parents=True,exist_ok=True);(s/'SERIES_STATE.json').write_text(json.dumps(state,ensure_ascii=False,indent=2))
base='https://github.com/seotro95/seotro/releases/download/kostenki-video-19-final-20m15s/'
bookmark=f'''# Chủ đề19 Kostenki — đã hoàn thành video20:15

[Tải video]({main['url']}) · [10cảnh mở đầu30giây]({base}KOSTENKI_19_OPENING_30s.mp4) · [5tiêu đề và prompt thumbnail]({base}KOSTENKI_19_TITLES_THUMBNAILS.txt).

Video1280×720,24fps,29.160khung hình. Chỉ voiceAnhAndrew đã lưu,đúng20:15;không tiếngclip,nhạc hoặcSFX. Đã giải mã toàn bộ,kiểm15điểm sóng âm không lệch thời gian,kiểmhashlinktảicôngkhai. Các cảnh thiếu dùng video liên quan,không ảnh đứng/bảng chữ. 100clip nguồn khác nhau,84clip được chọn;kiểmhình bằng mẫu,không xem tay liên tục. Hồ sơ ở video-19-kostenki/EDITING.

Bộ17voice,tài liệu,kịchbản,prompt và cấu hình giọng đã lưu vẫn giữ nguyên. Các giới hạn ràsoát bảnngữ đã nêu trong hồ sơvoice vẫn áp dụng. Không tự bắt đầu chủ đề tiếp theo. Giữ trạng thái các tập khác.

---

Nhật ký trước đó;trạng thái hiện tại ở đầu trang.

'''+(R/'BOOKMARK.edit_base.md').read_text()
(H/'productions/TIEP_TUC_TU_DAY.md').write_text(bookmark)
steps=(R/'PRODUCTION_STEPS.edit_base.md').read_text();steps=steps.replace('Hiện chưa có video hoàn chỉnh cho tập 19.','Video tập19 đã được dựng hoàn chỉnh theo yêu cầu mới; phần mở đầu dùng10cảnh trong30giây, thay kế hoạch12cảnh trước đó.')
steps+='''

## Bản dựng đã hoàn thành theo yêu cầu mới

1. Đối chiếu 100 video khác nhau sau khi bỏ các tên tải lên lặp. Lưu hash gốc và kiểm mẫu hình ở0,7/4,8/9,1giây mỗi clip. Tạo bản video im lặng720p24fps; chỉ thu hồi cache tải lại được, không xóa bản tải lên trong cuộc trò chuyện.
2. Đổi ánh xạ clip workbench thành prompt34. Hai mươi mã prompt thiếu được bù bằng cảnh động liên quan; lọc thêm cảnh vòng xương quá cao, chữ lớn hoặc sai bối cảnh. Bản cuối dùng84clip. Không dùng ảnh đứng hoặc bảng chữ thay cảnh.
3. Chốt10cảnh khác nhau cho30giây đầu, cắt theo ba câu đầu của voice. Dựng122mốc,121mốc10giây và5giây cuối. Chín dissolve0,4giây được bù phần chồng để tổng luôn20:15. Không cộng intro/outro ngoài voice.
4. Chỉ map video im lặng và voiceAnhAndrew đã bàn giao. Giữ lời,cao độ,timing; chuẩn hóa loudness hai lượt khi mã hóaAAC. Thêm12chương và phụ đềAnh tùy chọn,mặc định tắt.
5. Kiểm29.160khung hình,20:15,một đường tiếngAnh; giải mã toàn bộ,kiểm khoảng đen và15điểm đồng bộ sóng âm. Xem số đo trong FINAL_VIDEO_QA.json. Duyệt mẫu hình bản xuất ở mở đầu,chuyển chương,đoạn đã thay và phần kết.
6. Phát hành MP4 hoàn chỉnh,mở đầu30giây,TXT/ZIP năm cặp tiêu đề-thumbnail,dự án và hồ sơ. Không đưa clipnguồn,proxy,ảnh trích hoặc mã tải lên riêng tư vào dự án/GitHub. Kiểm digest máy chủ và hash toàn bộ MP4 tải công khai trước bàn giao.
'''
(P/'PRODUCTION_STEPS_APPLIED.md').write_text(steps)
readme=(O/'README.md').read_text()+'''\n\n[Kịch bản và12TXTprompt](https://github.com/seotro95/seotro/releases/download/kostenki-video-19-20m15s/KOSTENKI_VIDEO_19_TAI_LIEU_20m15s.zip) · [Quy trình đã lưu](PRODUCTION_STEPS_APPLIED.md) · [QA video](EDITING/FINAL_VIDEO_QA.json).\n'''
(P/'README.md').write_text(readme)
entries=[{'path':str(p.relative_to(H)),'mode':'100644','type':'blob','content':p.read_text()} for p in sorted(H.rglob('*')) if p.is_file()]
for e in entries:assert not re.search(r'file_[0-9a-f]{32}|/workspace/attachments/[0-9a-f]{8}-',e['content']),e['path']
groups=[];group=[];size=0
for e in entries:
 n=len(json.dumps(e,ensure_ascii=False).encode())
 if group and size+n>200000:groups.append(group);group=[];size=0
 group.append(e);size+=n
if group:groups.append(group)
for i,g in enumerate(groups):(R/f'final-git-group-{i}.json').write_text(json.dumps(g,ensure_ascii=False))
(R/'FINAL_GIT_STAGING.json').write_text(json.dumps({'files':len(entries),'groups':len(groups)},indent=2));print((R/'FINAL_GIT_STAGING.json').read_text())
