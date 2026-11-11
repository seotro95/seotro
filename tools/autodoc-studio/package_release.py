import hashlib,importlib.metadata,json,re,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;O=R/'release';O.mkdir(exist_ok=True);app=R/'dist/AutoDocStudio'
report=json.loads((R/'WINDOWS_TEST_REPORT.json').read_text());assert report['status']=='passed' and report['frozen_exe_tested']
for name in ['README.md','THIRD_PARTY.md','LICENSE','MO_TOOL.bat','WINDOWS_TEST_REPORT.json']:shutil.copyfile(R/name,app/name)
guide='''AUTODOC STUDIO1.0 — TỰ DỰNG VIDEO TRÊN WINDOWS

1. Giải nén AutoDocStudio-1.0.0-Windows-x64.zip. Giữ _internal cạnh AutoDocStudio.exe.
2. Mở AutoDocStudio.exe. Chọn tệp voiceAnh và thư mục video. Chọn nơi lưu hoặc dùng mặc định.
3. Bấm TỰ DỰNG VIDEO. Lần đầu cần Internet để tự tải FFmpeg và modelAI;không cần APIkey hoặc cài Python.
4. Khi xong,bấm Mở kết quả. VIDEO_HOAN_CHINH.mp4 là phim đã ghép và kiểm tra;TIMELINE.csv,SRTvà KIEM_TRA_VIDEO.json giúp xem lại.

Nguồn không bị sửa/xóa. Tiếng clip gốc bị loại;chỉ dùng tiếng từ filevoice.10cảnh/30giây đầu khi đủ nguồn. Cảnh thiếu dùng lại video liên quan;không tạo ảnh/bảng chữ để bù. Có720p/1080p,giảm cảnh lặp,chuyển cảnh ngắn,fadecuối,dừng và dùng lại cache.

Windows10/11 x64,khuyến nghị8GBRAM. CPU chạy được,không bắt buộc GPU. Lần đầu tải khoảng400MBcông cụ/model;một số bản FFmpeg/model có thể thay đổi kích thước. Thời gian dựng tùy cấu hình máy và độ dài phim.

AI so khớp theo tương đồng,có thể chọn sai ý hoặc sót trẻ em/chữ trong hình. Hãy dùng nguồn đã kiểm tra và xem kết quả trước khi đăng. Không cam kết biên tập chính xác như người hiểu nội dung khoa học. Model Whisperbase là mặc định;CLI có thể đổi --whisper-model small nếu muốn thử nhận dạng chính xác hơn.

Nếu lỗi:xem khung nhật ký,KIEM_TRA_VIDEO/STATUStrong dự án và %LOCALAPPDATA%\\AutoDocStudio\\last_error.log hoặc application.log. Đừng xóa clip gốc. Chạy lại cùng đầu vào/cài đặt dùng các đoạn đã hoàn thành;model chỉ tải một lần.
'''
(O/'HUONG_DAN_SU_DUNG.txt').write_text(guide,encoding='utf-8-sig');shutil.copyfile(O/'HUONG_DAN_SU_DUNG.txt',app/'HUONG_DAN_SU_DUNG.txt')
licenses=app/'THIRD_PARTY_LICENSES';licenses.mkdir(exist_ok=True);versions={}
for name in ['numpy','Pillow','onnxruntime','tokenizers','huggingface-hub','faster-whisper','ctranslate2','av','pyinstaller']:
    dist=importlib.metadata.distribution(name);versions[name]=dist.version
    for item in dist.files or []:
        if any(x in item.name.lower() for x in ['license','copying','notice']):
            src=Path(dist.locate_file(item))
            if src.is_file():
                # Normalize package-local paths; no upward path components in archive.
                dest=licenses/name/(str(item).replace('..','_').replace('/','__').replace('\\','__'))
                dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
(app/'DEPENDENCY_VERSIONS.json').write_text(json.dumps(versions,indent=2))
with zipfile.ZipFile(O/'AutoDocStudio-1.0.0-Windows-x64.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(app.rglob('*')):
        if p.is_file():z.write(p,'AutoDocStudio/'+p.relative_to(app).as_posix())
source_names=['main.py','requirements.txt','CAI_DAT.bat','MO_TOOL.bat','README.md','THIRD_PARTY.md','LICENSE','build_windows.ps1','package_release.py','windows_smoke.py']
with zipfile.ZipFile(O/'AutoDocStudio-1.0.0-Source.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in source_names:z.write(R/name,'AutoDocStudio-Source/'+name)
    for folder in ['autodoc','tests']:
        for p in (R/folder).rglob('*.py'):z.write(p,'AutoDocStudio-Source/'+p.relative_to(R).as_posix())
    for name in ['WINDOWS_TEST_REPORT.json','LOCAL_TEST_REPORT.json']:
        if (R/name).exists():z.write(R/name,'AutoDocStudio-Source/'+name)
shutil.copyfile(R/'WINDOWS_TEST_REPORT.json',O/'WINDOWS_TEST_REPORT.json')
assets=[]
for p in sorted(O.iterdir()):
    if p.is_file() and p.name not in ['SHA256SUMS.txt','RELEASE_MANIFEST.json']:assets.append({'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()})
(O/'SHA256SUMS.txt').write_text(''.join(x['sha256']+'  '+x['name']+'\n' for x in assets))
(O/'RELEASE_MANIFEST.json').write_text(json.dumps({'version':'1.0.0','model_weights_bundled':False,'ffmpeg_binaries_bundled':False,'user_media_bundled':False,'tested_frozen_windows_edit':True,'assets':assets},indent=2))
for p in O.glob('*.zip'):
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None
        assert not any('test-inputs/' in n or 'test-models/' in n or n.endswith(('.mp4','.mp3','.wav')) for n in z.namelist())
print(json.dumps({'status':'packaged','assets':assets},ensure_ascii=False),flush=True)
