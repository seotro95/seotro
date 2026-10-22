@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
if exist ".tools\ffmpeg\bin\ffmpeg.exe" set "PATH=%~dp0.tools\ffmpeg\bin;%PATH%"
if not defined VOICE_STUDIO_DATA_DIR set "VOICE_STUDIO_DATA_DIR=%~dp0.data"
if not exist ".venv\Scripts\python.exe" goto setup
if not exist "%VOICE_STUDIO_DATA_DIR%\models\vieneu_nano.ready" goto setup
if not exist "%VOICE_STUDIO_DATA_DIR%\models\vieneu_nano_clone.ready" goto setup
goto launch
:setup
call install.bat --no-pause
if errorlevel 1 goto fail
:launch
".venv\Scripts\python.exe" portable_launcher.py
set "VOICE_START_EXIT=%ERRORLEVEL%"
pause
exit /b %VOICE_START_EXIT%
:fail
echo Chua mo duoc tool. Kiem tra loi cai dat ben tren.
pause
exit /b 1
