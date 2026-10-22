@echo off
setlocal
cd /d "%~dp0"
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONUTF8=1"
set "VOICE_STUDIO_VARIANT=hmong"
if exist "..\runtime\python.exe" goto portable
if not exist "bundle_check.py" goto incomplete
if not exist "requirements-hmong.txt" goto incomplete
if exist ".venv-hmong\Scripts\python.exe" goto check_source
py -3.12 -c "import struct; assert struct.calcsize('P') == 8, 'Can Python 3.12 x64.'"
if errorlevel 1 (
 echo Can Python 3.12 x64 cho ma nguon. Ban ZIP Windows day du da kem Python, khong can tu cai.
 goto fail
)
py -3.12 bundle_check.py
if errorlevel 1 goto fail
py -3.12 -m venv .venv-hmong
if errorlevel 1 goto fail
:check_source
".venv-hmong\Scripts\python.exe" -c "import sys,struct; assert sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8, 'Can moi truong .venv-hmong Python 3.12 x64. Sao luu moi truong cu; khong xoa du lieu.'"
if errorlevel 1 goto fail
".venv-hmong\Scripts\python.exe" bundle_check.py
if errorlevel 1 goto fail
set "PATH=%CD%\ffmpeg\bin;%PATH%"
where ffmpeg >nul 2>&1
if errorlevel 1 goto prepare_ffmpeg
where ffprobe >nul 2>&1
if not errorlevel 1 goto dependencies
:prepare_ffmpeg
if not exist "packaging\build_windows.py" (
 echo Thieu FFmpeg/ffprobe va bo tai da xac minh. Dung goi Windows day du hoac bo ma nguon day du.
 goto fail
)
echo Dang tai FFmpeg tu nguon chinh thuc va kiem tra SHA256...
".venv-hmong\Scripts\python.exe" -c "import sys; from pathlib import Path; sys.path.insert(0, 'packaging'); from build_windows import download_verified_ffmpeg; download_verified_ffmpeg(Path('ffmpeg'), Path('.cache/hmong-downloads'))"
if errorlevel 1 goto fail
where ffmpeg >nul 2>&1
if errorlevel 1 goto fail
where ffprobe >nul 2>&1
if errorlevel 1 goto fail
:dependencies
".venv-hmong\Scripts\python.exe" -m pip install -r requirements-hmong.txt
if errorlevel 1 goto fail
".venv-hmong\Scripts\python.exe" -m pip check
if errorlevel 1 goto fail
".venv-hmong\Scripts\python.exe" hmong_launcher.py --setup-only
if errorlevel 1 goto fail
echo Da chuan bi xong. Mo start_hmong.bat de dung Voice Studio Hmong.
exit /b 0
:portable
if not exist "..\MO_VOICE_STUDIO_HMONG.bat" goto incomplete
call "..\MO_VOICE_STUDIO_HMONG.bat" --setup-only
exit /b %ERRORLEVEL%
:incomplete
echo Thieu tep bat buoc. Giai nen TOAN BO ZIP Windows va mo MO_VOICE_STUDIO_HMONG.bat.
:fail
echo Cai dat Hmong that bai. Xem loi ben tren. Moi truong tieng Viet va du lieu ca nhan duoc giu nguyen.
pause
exit /b 1
