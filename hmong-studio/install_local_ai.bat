@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  python -m venv .venv
  if errorlevel 1 goto fail
)
echo Cai PyTorch CPU tu nguon chinh thuc. Co the can vai tram MB.
.venv\Scripts\python.exe -m pip install "torch>=2.4,<3" --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements-local.txt
if errorlevel 1 goto fail
where ffmpeg >nul 2>nul
if errorlevel 1 echo Can cai FFmpeg trong PATH de nhan dang audio. Xem README.md.
echo Da cai thu vien AI. Mo hinh chua duoc tai. Xem README.md de chon mo hinh.
echo Khong tu dong kich hoat nhan ban giong hoac cam xuc.
pause
exit /b 0
:fail
echo Cai dat that bai. Giu thong bao loi de kiem tra, khong tat xac minh TLS.
pause
exit /b 1
