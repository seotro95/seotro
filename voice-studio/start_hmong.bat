@echo off
setlocal
cd /d "%~dp0"
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONUTF8=1"
set "VOICE_STUDIO_VARIANT=hmong"
if exist "..\runtime\python.exe" goto portable
if exist ".venv-hmong\Scripts\python.exe" goto source
if not exist "install_hmong.bat" goto incomplete
echo Dang chuan bi moi truong Hmong rieng cho lan dau...
call install_hmong.bat
if errorlevel 1 goto fail
:source
".venv-hmong\Scripts\python.exe" hmong_launcher.py %*
set "VOICE_EXIT=%ERRORLEVEL%"
if not "%VOICE_EXIT%"=="0" pause
exit /b %VOICE_EXIT%
:portable
if not exist "..\MO_VOICE_STUDIO_HMONG.bat" goto incomplete
call "..\MO_VOICE_STUDIO_HMONG.bat" %*
exit /b %ERRORLEVEL%
:incomplete
echo Bo tool thieu tep bat buoc. Giai nen TOAN BO ZIP va mo MO_VOICE_STUDIO_HMONG.bat.
:fail
echo Khong mo duoc Hmong Studio. Xem thong bao loi ben tren. Du lieu ca nhan duoc giu nguyen.
pause
exit /b 1
