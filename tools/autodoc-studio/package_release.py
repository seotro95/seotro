import hashlib,importlib.metadata,json,os,shutil,zipfile
from pathlib import Path
from autodoc.resources import prepare_distribution,validate_archive,VAD_ASSET,VAD_ARCHIVE_PATH,VAD_SHA256
R=Path(__file__).resolve().parent;O=R/'release';O.mkdir(exist_ok=True);app=R/'dist/AutoDocStudio'
vad_resource=prepare_distribution(app)
report=json.loads((R/'WINDOWS_TEST_REPORT.json').read_text(encoding='utf-8-sig'));assert report['status']=='passed' and report['frozen_exe_tested'] and report['frozen_gui_preview_tested']
gui_report=json.loads((R/'GUI_FEATURE_REPORT.json').read_text(encoding='utf-8-sig'));assert gui_report['status']=='passed' and all(gui_report['checks'].values())
multilingual=json.loads((R/'MULTILINGUAL_TEST_REPORT.json').read_text(encoding='utf-8-sig'));assert multilingual['status']=='passed' and multilingual['frozen_exe_tested']
for name in ['README.md','THIRD_PARTY.md','LICENSE','MO_TOOL.bat','WINDOWS_TEST_REPORT.json','GUI_FEATURE_REPORT.json','MULTILINGUAL_TEST_REPORT.json']:shutil.copyfile(R/name,app/name)
guide='''AUTODOC STUDIO 2.3 FULL — NGANG 16:9 / DỌC 9:16 — WINDOWS 10/11 X64

Giải nén ZIP, giữ _internal cạnh AutoDocStudio.exe, mở EXE.
Chọn Tỷ lệ video 16:9 ngang hoặc 9:16 dọc ngay dưới đầu vào; cũng có trong AI / xuất và Xuất video. 720 xuất 1280x720 hoặc 720x1280; 1080 xuất 1920x1080 hoặc 1080x1920. fill cắt kín khung, contain giữ toàn cảnh và thêm viền đen, không kéo méo. Logo/phụ đề/preview theo tỷ lệ đã chọn, voice giữ nguyên thời lượng.
Ngôn ngữ mặc định auto. Tool nhận lời theo ngôn ngữ gốc, giữ nguyên voice và phụ đề, dùng bản dịch tiếng Anh cùng mốc để chọn hình. Có thể nhập TXT/SRT tiếng Anh ở Tham chiếu Anh. H’Mông: chọn hmn, cung cấp SRT tham chiếu Anh đúng mốc; thêm SRT H’Mông nếu muốn phụ đề H’Mông. Không có nhận dạng H’Mông tự động đáng tin cậy.
1. Chọn voice + thư mục ảnh/video + nơi lưu. TXT/SRT là tùy chọn.
2. Bấm TỰ ĐỘNG EDIT & XUẤT để tool làm trọn quy trình rồi lưu video và dự án. Không cần bấm Xuất thêm. Cài định dạng, độ phân giải, FPS, chất lượng và tên video ở tab AI / xuất trước khi chạy. Bản sau tự đánh số, giữ video đã xuất trước đó.
   Nếu muốn sửa trước: bấm Tự xếp cảnh. Chọn cảnh để xem hình, phát voice và chỉnh nguồn, cắt/phóng, tốc độ, hiệu ứng, chuyển cảnh. Chia tại con trỏ hoặc gộp cảnh trước; tổng thời lượng voice không đổi.
3. Tab Logo / tiếng: chèn logo, vị trí/cỡ/độ hiện; mặc định TẮT tiếng clip gốc. Bỏ chọn để giữ/trộn tiếng clip cùng voice.
4. Tab Phụ đề: sửa câu/mốc, nhập/xuất TXT/SRT, chọn phông/màu/cỡ/đậm/nghiêng/viền/nền. burn ghi kiểu chữ vào hình; soft bật/tắt ở trình phát, kiểu phụ thuộc trình phát; none không phụ đề.
5. Lưu dự án để mở sửa lần sau. Giữ media gốc và thư mục dự án/cache đúng vị trí. Bấm Xuất video để chọn tên/nơi lưu, MP4/MKV,720/1080p,FPS,chất lượng và CPU/GPU. Video được lưu khi xuất xong; báo cáo .qa.json nằm cạnh video.
6. Có sẵn 20 hiệu ứng/chuyển động và 19 chuyển cảnh. Nút Tải gói hiệu ứng bổ sung vẫn tìm và kiểm gói chính thức rồi cài preset khi cần.

Nhanh hơn nhờ cache nhận diện dùng lại giữa dự án, đọc khung hình bằng PyAV, hai cảnh dựng song song và cache từng cảnh. SRT đúng mốc bỏ qua chép lời gốc; voice ngoại ngữ vẫn cần dịch để chọn hình nếu không có tham chiếu Anh. fast lấy một mẫu/cảnh; balanced/quality lấy ba mẫu. auto thử GPU thật rồi quay về CPU khi cần. Tốc độ tùy máy; không có cam kết số lần tăng tốc.

Lần đầu cần mạng tải FFmpeg/model,không cần API trả phí hoặc Python với bản EXE. Cache dùng chung v1. Windows x64,khuyến nghị RAM8GB+. Dự án dài nên có vài GB trống. Model Whisper/CLIP lớn được tải riêng; model VAD nhỏ bắt buộc đã kèm trong ZIP. Media người dùng không nằm trong ZIP.

AI khớp hình và lọc trẻ em chỉ là ước lượng; hãy xem lại trước đăng. Nguồn không bị sửa. Đổi logo/phụ đề burn sẽ dựng lại mọi cảnh có thay đổi. Soft subtitle không hiển thị trong preview tích hợp.

Xem KIEM_TRA_CHUC_NANG.txt để biết các chức năng đã thử trên bản EXE, README.md để biết cách dùng/giới hạn. Lỗi:khung nhật ký hoặc %LOCALAPPDATA%/AutoDocStudio/last_error.log,application.log. Dừng tác vụ giữ cache đã hoàn thành.
'''
(O/'HUONG_DAN_SU_DUNG.txt').write_text(guide,encoding='utf-8-sig');shutil.copyfile(O/'HUONG_DAN_SU_DUNG.txt',app/'HUONG_DAN_SU_DUNG.txt')
rows=[
    ('Tự động edit dọc 9:16 720x1280 và preview đúng chiều',gui_report['checks']['automatic_portrait_9_16_720x1280'] and gui_report['checks']['portrait_preview_orientation_correct']),
    ('Tự động edit một lần bấm, không cần SRT',gui_report['checks']['one_click_automatic_gui_without_subtitles']),
    ('Voice Việt/Tây Ban Nha/Nhật: tự nhận diện, lời gốc và lời Anh chọn hình tách riêng',multilingual['status']=='passed'),
    ('Voice H’Mông: dựng bằng SRT tham chiếu Anh; không dùng ASR H’Mông',multilingual['hmong_is_timed_english_reference_mode_not_speech_recognition']),
 ('Mở đầu tự động 10 cảnh / 30 giây',gui_report['checks']['automatic_ten_scene_30_second_opening']),
 ('Nhận cả ảnh và video',report['mixed_image_video_import']),
 ('Voice khớp thời lượng, tắt/giữ tiếng nguồn',report['mute_and_keep_source_audio_verified'] and report['source_tone_verified']),
 ('Logo và phụ đề được kiểm tra trên pixel video xuất',report['logo_pixels_verified'] and report['burn_subtitle_pixels_verified']),
 ('Phụ đề TXT/SRT nhập/xuất; thêm/sửa/xóa câu',gui_report['checks']['import_export_txt_and_srt'] and gui_report['checks']['subtitle_edit_add_delete']),
 ('Phông, màu, cỡ, đậm/nghiêng, viền/nền, vị trí; logo và âm lượng',gui_report['checks']['logo_audio_and_subtitle_style_controls']),
 ('Preview phát/dừng/tua; sửa nguồn, tốc độ, crop, tâm cắt',gui_report['checks']['play_pause_seek_preview'] and gui_report['checks']['scene_edit_controls'] and gui_report['checks']['click_crop_focus']),
 ('Chia/gộp/đổi nguồn; tổng thời lượng voice giữ nguyên',gui_report['checks']['split_merge_preserves_voice_duration'] and gui_report['checks']['move_source_controls']),
 ('Lưu và mở lại dự án',gui_report['checks']['save_and_reopen_project']),
 ('Xuất MP4/MKV; 720p và 1080p; 24/25/30 FPS',report['mp4_and_mkv_verified'] and gui_report['checks']['manual_export_dialog_1080p_25fps']),
 ('60 FPS: kiểm tra render cảnh ngắn',report['short_scene_60fps_rendered']),
 ('20 hiệu ứng và 19 chuyển cảnh: render từng kiểu',report['all_20_effects_rendered'] and report['all_19_transitions_rendered']),
 ('Tải và cài gói hiệu ứng',gui_report['checks']['download_install_effect_pack']),
 ('Dừng, chạy lại và giữ bản xuất cũ',gui_report['checks']['cancel_keeps_completed_video'] and gui_report['checks']['repeat_auto_keeps_previous_export']),
 ('Cache nhận diện/cảnh xuất dùng lại',report['scene_cache_reused'] and report['shared_feature_cache_hits']>0)]
assert all(ok for _,ok in rows)
check_text='AUTODOC STUDIO 2.3.0 — KIỂM TRA CHỨC NĂNG TRÊN WINDOWS EXE\n\n'+'\n'.join('ĐẠT — '+name for name,ok in rows)+'\n\nCPU và chế độ tự quay về CPU đã chạy thử. Chưa kiểm thử mã hóa trên GPU vật lý NVIDIA/Intel/AMD.\nPreview đã kiểm thao tác và hình phát; thiết bị/loa thực tế của người dùng cần hoạt động để nghe.\nAI chọn cảnh và lọc trẻ em là ước lượng, không phải bảo đảm hiểu đúng nội dung.\nLần đầu cần mạng tải FFmpeg/model; bản Full có đầy đủ chức năng, VAD nhỏ được kèm; model Whisper/CLIP lớn và FFmpeg tải riêng.\n'
(O/'KIEM_TRA_CHUC_NANG.txt').write_text(check_text,encoding='utf-8-sig');shutil.copyfile(O/'KIEM_TRA_CHUC_NANG.txt',app/'KIEM_TRA_CHUC_NANG.txt')
licenses=app/'THIRD_PARTY_LICENSES';licenses.mkdir(exist_ok=True);versions={}
# prepare_distribution prunes only unused ONNX Runtime examples.
# The required faster-whisper VAD model stays in the delivered archive.
for name in ['numpy','Pillow','onnxruntime','tokenizers','huggingface-hub','faster-whisper','ctranslate2','av','pyinstaller','langid']:
    dist=importlib.metadata.distribution(name);versions[name]=dist.version
    for item in dist.files or []:
        if any(x in item.name.lower() for x in ['license','copying','notice']):
            src=Path(dist.locate_file(item))
            if src.is_file():
                dest=licenses/name/(str(item).replace('..','_').replace('/','__').replace('\\','__'));dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
for name in ['SILERO_VAD_LICENSE.txt','FASTER_WHISPER_LICENSE.txt']:
    shutil.copyfile(R/name,licenses/name)
(app/'DEPENDENCY_VERSIONS.json').write_text(json.dumps(versions,indent=2))
for p in (R/'effect_packs').glob('*.json'):
    # Git on Windows may check text out as CRLF. The manifest hashes canonical
    # UTF-8/LF bytes, so preserve those exact bytes in both deliveries.
    data=p.read_text(encoding='utf-8').encode('utf-8');dest=app/'effect_packs'/p.name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(data);(O/p.name).write_bytes(data)
pack_manifest=json.loads((O/'manifest.json').read_text(encoding='utf-8-sig'));assert hashlib.sha256((O/'cinematic-extras.json').read_bytes()).hexdigest()==pack_manifest['sha256']
with zipfile.ZipFile(O/'AutoDocStudio-2.3.0-Full-Windows-x64.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(app.rglob('*')):
        if p.is_file():z.write(p,'AutoDocStudio/'+p.relative_to(app).as_posix())
validate_archive(O/'AutoDocStudio-2.3.0-Full-Windows-x64.zip')
repair_guide='''SỬA LỖI THIẾU SILERO VAD TRONG AUTODOC STUDIO 2.2.0

1. Đóng tool.
2. Giải nén toàn bộ SUA_LOI_VAD_2.2.0.zip vào THƯ MỤC CHỨA AutoDocStudio.exe.
   Gộp thư mục _internal nếu được hỏi. Không chọn thư mục _internal làm nơi giải nén.
3. Kiểm tra có file _internal/faster_whisper/assets/silero_vad_v6.onnx rồi mở lại tool.

Bản vá chỉ bổ sung model VAD bắt buộc và giấy phép, không đổi EXE, voice, video hay dự án.
Có thể dùng bản Full 2.3.0 thay thế. Giữ _internal cạnh EXE, không cần xóa cache/model đã tải.
'''
(O/'HUONG_DAN_VA_VAD.txt').write_text(repair_guide,encoding='utf-8-sig')
with zipfile.ZipFile(O/'SUA_LOI_VAD_2.2.0.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    z.write(app/'_internal/faster_whisper/assets'/VAD_ASSET,'_internal/faster_whisper/assets/'+VAD_ASSET)
    z.writestr('HUONG_DAN_VA_VAD.txt',repair_guide.encode('utf-8-sig'))
    for name in ['SILERO_VAD_LICENSE.txt','FASTER_WHISPER_LICENSE.txt']:z.write(R/name,'VAD_LICENSES/'+name)
names=['main.py','requirements.txt','CAI_DAT.bat','MO_TOOL.bat','README.md','THIRD_PARTY.md','LICENSE','build_windows.ps1','package_release.py','windows_smoke.py','multilingual_smoke.py','windows-workflow.yml','verify_delivery.py','SILERO_VAD_LICENSE.txt','FASTER_WHISPER_LICENSE.txt']
with zipfile.ZipFile(O/'AutoDocStudio-2.3.0-Source.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in names:z.write(R/name,'AutoDocStudio-Source/'+name)
    for folder,pattern in [('autodoc','*.py'),('tests','*.py'),('effect_packs','*.json')]:
        for p in (R/folder).rglob(pattern):z.write(p,'AutoDocStudio-Source/'+p.relative_to(R).as_posix())
    for name in ['WINDOWS_TEST_REPORT.json','LOCAL_TEST_REPORT.json','GUI_FEATURE_REPORT.json','MULTILINGUAL_TEST_REPORT.json']:
        if (R/name).exists():z.write(R/name,'AutoDocStudio-Source/'+name)
shutil.copyfile(R/'WINDOWS_TEST_REPORT.json',O/'WINDOWS_TEST_REPORT.json');shutil.copyfile(R/'GUI_FEATURE_REPORT.json',O/'GUI_FEATURE_REPORT.json');shutil.copyfile(R/'MULTILINGUAL_TEST_REPORT.json',O/'MULTILINGUAL_TEST_REPORT.json');assets=[]
for p in sorted(O.iterdir()):
    if p.is_file() and p.name not in ['SHA256SUMS.txt','RELEASE_MANIFEST.json']:assets.append({'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()})
(O/'SHA256SUMS.txt').write_text(''.join(x['sha256']+'  '+x['name']+'\n' for x in assets));(O/'RELEASE_MANIFEST.json').write_text(json.dumps({'version':'2.3.0','build_commit':os.environ.get('GITHUB_SHA'),'build_run_id':os.environ.get('GITHUB_RUN_ID'),'large_model_weights_bundled':False,'required_runtime_models_bundled':[vad_resource],'ffmpeg_binaries_bundled':False,'user_media_bundled':False,'tested_frozen_windows_edit_and_preview':True,'assets':assets},indent=2))
for p in O.glob('*.zip'):
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None
        allowed_onnx={VAD_ARCHIVE_PATH,'_internal/faster_whisper/assets/'+VAD_ASSET}
        blocked=[n for n in z.namelist() if n.endswith(('.mp4','.mp3','.wav')) or (n.endswith('.onnx') and n not in allowed_onnx) or 'windows test/' in n or 'local test/' in n or (n.endswith(('.jpg','.png')) and '/_internal/' not in n)]
        assert not blocked,blocked[:20]
print(json.dumps({'status':'packaged','assets':assets}),flush=True)
