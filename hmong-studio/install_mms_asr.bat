@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 1
set "PYTHONUTF8=1"
call setup_env.bat
if errorlevel 1 goto fail
echo Cai PyTorch CPU tu nguon chinh thuc. Co the can vai tram MB.
.venv\Scripts\python.exe -m pip install --no-input --only-binary=:all: "torch>=2.4,<3" --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install --no-input --only-binary=:all: -r requirements-local.txt
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip check
if errorlevel 1 goto fail
where ffmpeg >nul 2>nul
if errorlevel 1 echo Can cai FFmpeg trong PATH de nhan dang audio. Xem README.md.
echo Da cai thu vien AI. Mo hinh chua duoc tai. Xem README.md de chon mo hinh.
echo Thu vien MMS khong tu them mo hinh nhan ban Hmong Trang.
pause
exit /b 0
:fail
echo Cai dat that bai. Xem loi ben tren. Bo cai chi dung Python 3.10-3.12 64-bit.
echo Khong can cai Visual C++ chi de sua loi Python 3.15 trong anh.
echo Khong tat xac minh TLS; neu thieu wheel, giu thong bao loi de kiem tra.
pause
exit /b 1
