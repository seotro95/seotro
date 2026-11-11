import hashlib,importlib.metadata,json,os,shutil,zipfile
from pathlib import Path
R=Path(__file__).resolve().parent;O=R/'release';O.mkdir(exist_ok=True);app=R/'dist/AutoDocStudio'
report=json.loads((R/'WINDOWS_TEST_REPORT.json').read_text(encoding='utf-8-sig'));assert report['status']=='passed' and report['frozen_exe_tested'] and report['frozen_gui_preview_tested']
gui_report=json.loads((R/'GUI_FEATURE_REPORT.json').read_text(encoding='utf-8-sig'));assert gui_report['status']=='passed' and all(gui_report['checks'].values())
for name in ['README.md','THIRD_PARTY.md','LICENSE','MO_TOOL.bat','WINDOWS_TEST_REPORT.json','GUI_FEATURE_REPORT.json']:shutil.copyfile(R/name,app/name)
guide='''AUTODOC STUDIO 2.1 FULL — WINDOWS 10/11 X64

Giải nén ZIP, giữ _internal cạnh AutoDocStudio.exe, mở EXE.
1. Chọn voice + thư mục ảnh/video + nơi lưu. TXT/SRT là tùy chọn.
2. Bấm TỰ ĐỘNG EDIT & XUẤT để tool làm trọn quy trình rồi lưu video và dự án. Không cần bấm Xuất thêm. Cài định dạng, độ phân giải, FPS, chất lượng và tên video ở tab AI / xuất trước khi chạy. Bản sau tự đánh số, giữ video đã xuất trước đó.
   Nếu muốn sửa trước: bấm Tự xếp cảnh. Chọn cảnh để xem hình, phát voice và chỉnh nguồn, cắt/phóng, tốc độ, hiệu ứng, chuyển cảnh. Chia tại con trỏ hoặc gộp cảnh trước; tổng thời lượng voice không đổi.
3. Tab Logo / tiếng: chèn logo, vị trí/cỡ/độ hiện; mặc định TẮT tiếng clip gốc. Bỏ chọn để giữ/trộn tiếng clip cùng voice.
4. Tab Phụ đề: sửa câu/mốc, nhập/xuất TXT/SRT, chọn phông/màu/cỡ/đậm/nghiêng/viền/nền. burn ghi kiểu chữ vào hình; soft bật/tắt ở trình phát, kiểu phụ thuộc trình phát; none không phụ đề.
5. Lưu dự án để mở sửa lần sau. Giữ media gốc và thư mục dự án/cache đúng vị trí. Bấm Xuất video để chọn tên/nơi lưu, MP4/MKV,720/1080p,FPS,chất lượng và CPU/GPU. Video được lưu khi xuất xong; báo cáo .qa.json nằm cạnh video.
6. Có sẵn 20 hiệu ứng/chuyển động và 19 chuyển cảnh. Nút Tải gói hiệu ứng bổ sung vẫn tìm và kiểm gói chính thức rồi cài preset khi cần.

Nhanh hơn nhờ cache nhận diện dùng lại giữa dự án, đọc khung hình bằng PyAV, hai cảnh dựng song song và cache từng cảnh. Có SRT đúng mốc sẽ bỏ qua nhận dạng voice. fast lấy một mẫu/cảnh; balanced/quality lấy ba mẫu. auto thử GPU thật rồi quay về CPU khi cần. Tốc độ tùy máy; không có cam kết số lần tăng tốc.

Lần đầu cần mạng tải FFmpeg/model,không cần API trả phí hoặc Python với bản EXE. Cache dùng chung v1. Windows x64,khuyến nghị RAM8GB+. Dự án dài nên có vài GB trống. Model/cache/media người dùng không nằm trong ZIP.

AI khớp hình và lọc trẻ em chỉ là ước lượng; hãy xem lại trước đăng. Nguồn không bị sửa. Đổi logo/phụ đề burn sẽ dựng lại mọi cảnh có thay đổi. Soft subtitle không hiển thị trong preview tích hợp.

Xem KIEM_TRA_CHUC_NANG.txt để biết các chức năng đã thử trên bản EXE, README.md để biết cách dùng/giới hạn. Lỗi:khung nhật ký hoặc %LOCALAPPDATA%/AutoDocStudio/last_error.log,application.log. Dừng tác vụ giữ cache đã hoàn thành.
'''
(O/'HUONG_DAN_SU_DUNG.txt').write_text(guide,encoding='utf-8-sig');shutil.copyfile(O/'HUONG_DAN_SU_DUNG.txt',app/'HUONG_DAN_SU_DUNG.txt')
rows=[
 ('Tự động edit một lần bấm, không cần SRT',gui_report['checks']['one_click_automatic_gui_without_subtitles']),
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
check_text='AUTODOC STUDIO 2.1.0 — KIỂM TRA CHỨC NĂNG TRÊN WINDOWS EXE\n\n'+'\n'.join('ĐẠT — '+name for name,ok in rows)+'\n\nCPU và chế độ tự quay về CPU đã chạy thử. Chưa kiểm thử mã hóa trên GPU vật lý NVIDIA/Intel/AMD.\nPreview đã kiểm thao tác và hình phát; thiết bị/loa thực tế của người dùng cần hoạt động để nghe.\nAI chọn cảnh và lọc trẻ em là ước lượng, không phải bảo đảm hiểu đúng nội dung.\nLần đầu cần mạng tải FFmpeg/model; bản Full có đầy đủ chức năng, không kèm model/FFmpeg trong ZIP.\n'
(O/'KIEM_TRA_CHUC_NANG.txt').write_text(check_text,encoding='utf-8-sig');shutil.copyfile(O/'KIEM_TRA_CHUC_NANG.txt',app/'KIEM_TRA_CHUC_NANG.txt')
licenses=app/'THIRD_PARTY_LICENSES';licenses.mkdir(exist_ok=True);versions={}
# collect-all includes tiny ONNX Runtime example models; they are unused by the
# editor and are not the CLIP models. Keep the portable package model-free.
for p in (app/'_internal').rglob('*.onnx'):p.unlink()
for name in ['numpy','Pillow','onnxruntime','tokenizers','huggingface-hub','faster-whisper','ctranslate2','av','pyinstaller']:
    dist=importlib.metadata.distribution(name);versions[name]=dist.version
    for item in dist.files or []:
        if any(x in item.name.lower() for x in ['license','copying','notice']):
            src=Path(dist.locate_file(item))
            if src.is_file():
                dest=licenses/name/(str(item).replace('..','_').replace('/','__').replace('\\','__'));dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
(app/'DEPENDENCY_VERSIONS.json').write_text(json.dumps(versions,indent=2))
for p in (R/'effect_packs').glob('*.json'):
    # Git on Windows may check text out as CRLF. The manifest hashes canonical
    # UTF-8/LF bytes, so preserve those exact bytes in both deliveries.
    data=p.read_text(encoding='utf-8').encode('utf-8');dest=app/'effect_packs'/p.name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(data);(O/p.name).write_bytes(data)
pack_manifest=json.loads((O/'manifest.json').read_text(encoding='utf-8-sig'));assert hashlib.sha256((O/'cinematic-extras.json').read_bytes()).hexdigest()==pack_manifest['sha256']
with zipfile.ZipFile(O/'AutoDocStudio-2.1.0-Full-Windows-x64.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(app.rglob('*')):
        if p.is_file():z.write(p,'AutoDocStudio/'+p.relative_to(app).as_posix())
names=['main.py','requirements.txt','CAI_DAT.bat','MO_TOOL.bat','README.md','THIRD_PARTY.md','LICENSE','build_windows.ps1','package_release.py','windows_smoke.py','windows-workflow.yml']
with zipfile.ZipFile(O/'AutoDocStudio-2.1.0-Source.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in names:z.write(R/name,'AutoDocStudio-Source/'+name)
    for folder,pattern in [('autodoc','*.py'),('tests','*.py'),('effect_packs','*.json')]:
        for p in (R/folder).rglob(pattern):z.write(p,'AutoDocStudio-Source/'+p.relative_to(R).as_posix())
    for name in ['WINDOWS_TEST_REPORT.json','LOCAL_TEST_REPORT.json','GUI_FEATURE_REPORT.json']:
        if (R/name).exists():z.write(R/name,'AutoDocStudio-Source/'+name)
shutil.copyfile(R/'WINDOWS_TEST_REPORT.json',O/'WINDOWS_TEST_REPORT.json');shutil.copyfile(R/'GUI_FEATURE_REPORT.json',O/'GUI_FEATURE_REPORT.json');assets=[]
for p in sorted(O.iterdir()):
    if p.is_file() and p.name not in ['SHA256SUMS.txt','RELEASE_MANIFEST.json']:assets.append({'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()})
(O/'SHA256SUMS.txt').write_text(''.join(x['sha256']+'  '+x['name']+'\n' for x in assets));(O/'RELEASE_MANIFEST.json').write_text(json.dumps({'version':'2.1.0','build_commit':os.environ.get('GITHUB_SHA'),'build_run_id':os.environ.get('GITHUB_RUN_ID'),'model_weights_bundled':False,'ffmpeg_binaries_bundled':False,'user_media_bundled':False,'tested_frozen_windows_edit_and_preview':True,'assets':assets},indent=2))
for p in O.glob('*.zip'):
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None
        blocked=[n for n in z.namelist() if n.endswith(('.mp4','.mp3','.wav','.onnx')) or 'windows test/' in n or 'local test/' in n or (n.endswith(('.jpg','.png')) and '/_internal/' not in n)]
        assert not blocked,blocked[:20]
print(json.dumps({'status':'packaged','assets':assets}),flush=True)
