import hashlib,importlib.metadata,json,shutil,zipfile
from pathlib import Path
R=Path(__file__).resolve().parent;O=R/'release';O.mkdir(exist_ok=True);app=R/'dist/AutoDocStudio'
report=json.loads((R/'WINDOWS_TEST_REPORT.json').read_text());assert report['status']=='passed' and report['frozen_exe_tested'] and report['frozen_gui_preview_tested']
for name in ['README.md','THIRD_PARTY.md','LICENSE','MO_TOOL.bat','WINDOWS_TEST_REPORT.json']:shutil.copyfile(R/name,app/name)
guide='''AUTODOC STUDIO 2.0 — WINDOWS 10/11 X64

Giải nén ZIP, giữ _internal cạnh AutoDocStudio.exe, mở EXE.
1. Chọn voice + thư mục ảnh/video + nơi lưu. TXT/SRT là tùy chọn.
2. Bấm Tự xếp cảnh. Chọn cảnh để xem hình, phát voice và chỉnh nguồn, cắt/phóng, tốc độ, hiệu ứng, chuyển cảnh. Chia tại con trỏ hoặc gộp cảnh trước; tổng thời lượng voice không đổi.
3. Tab Logo / tiếng: chèn logo, vị trí/cỡ/độ hiện; mặc định TẮT tiếng clip gốc. Bỏ chọn để giữ/trộn tiếng clip cùng voice.
4. Tab Phụ đề: sửa câu/mốc, nhập/xuất TXT/SRT, chọn phông/màu/cỡ/đậm/nghiêng/viền/nền. burn ghi kiểu chữ vào hình; soft bật/tắt ở trình phát, kiểu phụ thuộc trình phát; none không phụ đề.
5. Lưu dự án để mở sửa lần sau. Giữ media gốc và thư mục dự án/cache đúng vị trí. Bấm Xuất video để chọn tên/nơi lưu, MP4/MKV,720/1080p,FPS,chất lượng và CPU/GPU. Video được lưu khi xuất xong; báo cáo .qa.json nằm cạnh video.
6. Tải gói hiệu ứng bổ sung trong tab Cảnh: tool tìm và kiểm gói chính thức rồi cài preset. Không cần cài tay.

Nhanh hơn nhờ cache nhận diện dùng lại giữa dự án, đọc khung hình bằng PyAV, hai cảnh dựng song song và cache từng cảnh. Có SRT đúng mốc sẽ bỏ qua nhận dạng voice. fast lấy một mẫu/cảnh; balanced/quality lấy ba mẫu. auto thử GPU thật rồi quay về CPU khi cần. Tốc độ tùy máy; không có cam kết số lần tăng tốc.

Lần đầu cần mạng tải FFmpeg/model,không cần API trả phí hoặc Python với bản EXE. Cache dùng chung v1. Windows x64,khuyến nghị RAM8GB+. Dự án dài nên có vài GB trống. Model/cache/media người dùng không nằm trong ZIP.

AI khớp hình và lọc trẻ em chỉ là ước lượng; hãy xem lại trước đăng. Nguồn không bị sửa. Đổi logo/phụ đề burn sẽ dựng lại mọi cảnh có thay đổi. Soft subtitle không hiển thị trong preview tích hợp.

Xem README.md để biết đủ chức năng,CLI và giới hạn. Lỗi:khung nhật ký hoặc %LOCALAPPDATA%/AutoDocStudio/last_error.log,application.log. Dừng tác vụ giữ cache đã hoàn thành.
'''
(O/'HUONG_DAN_SU_DUNG.txt').write_text(guide,encoding='utf-8-sig');shutil.copyfile(O/'HUONG_DAN_SU_DUNG.txt',app/'HUONG_DAN_SU_DUNG.txt')
licenses=app/'THIRD_PARTY_LICENSES';licenses.mkdir(exist_ok=True);versions={}
for name in ['numpy','Pillow','onnxruntime','tokenizers','huggingface-hub','faster-whisper','ctranslate2','av','pyinstaller']:
    dist=importlib.metadata.distribution(name);versions[name]=dist.version
    for item in dist.files or []:
        if any(x in item.name.lower() for x in ['license','copying','notice']):
            src=Path(dist.locate_file(item))
            if src.is_file():
                dest=licenses/name/(str(item).replace('..','_').replace('/','__').replace('\\','__'));dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
(app/'DEPENDENCY_VERSIONS.json').write_text(json.dumps(versions,indent=2))
for p in (R/'effect_packs').glob('*.json'):
    dest=app/'effect_packs'/p.name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(p,dest);shutil.copyfile(p,O/p.name)
with zipfile.ZipFile(O/'AutoDocStudio-2.0.0-Windows-x64.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(app.rglob('*')):
        if p.is_file():z.write(p,'AutoDocStudio/'+p.relative_to(app).as_posix())
names=['main.py','requirements.txt','CAI_DAT.bat','MO_TOOL.bat','README.md','THIRD_PARTY.md','LICENSE','build_windows.ps1','package_release.py','windows_smoke.py','windows-workflow.yml']
with zipfile.ZipFile(O/'AutoDocStudio-2.0.0-Source.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in names:z.write(R/name,'AutoDocStudio-Source/'+name)
    for folder,pattern in [('autodoc','*.py'),('tests','*.py'),('effect_packs','*.json')]:
        for p in (R/folder).rglob(pattern):z.write(p,'AutoDocStudio-Source/'+p.relative_to(R).as_posix())
    for name in ['WINDOWS_TEST_REPORT.json','LOCAL_TEST_REPORT.json']:
        if (R/name).exists():z.write(R/name,'AutoDocStudio-Source/'+name)
shutil.copyfile(R/'WINDOWS_TEST_REPORT.json',O/'WINDOWS_TEST_REPORT.json');assets=[]
for p in sorted(O.iterdir()):
    if p.is_file() and p.name not in ['SHA256SUMS.txt','RELEASE_MANIFEST.json']:assets.append({'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()})
(O/'SHA256SUMS.txt').write_text(''.join(x['sha256']+'  '+x['name']+'\n' for x in assets));(O/'RELEASE_MANIFEST.json').write_text(json.dumps({'version':'2.0.0','model_weights_bundled':False,'ffmpeg_binaries_bundled':False,'user_media_bundled':False,'tested_frozen_windows_edit_and_preview':True,'assets':assets},indent=2))
for p in O.glob('*.zip'):
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None;assert not any(n.endswith(('.mp4','.mp3','.wav','.jpg','.png','.onnx')) or 'windows test/' in n or 'local test/' in n for n in z.namelist())
print(json.dumps({'status':'packaged','assets':assets}),flush=True)
