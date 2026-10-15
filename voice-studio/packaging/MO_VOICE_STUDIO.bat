@echo off
setlocal
cd /d "%~dp0"
set "PATH=%~dp0runtime;%~dp0ffmpeg\bin;%PATH%"
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONUTF8=1"
set "VOICE_STUDIO_DATA_DIR=%~dp0voice-studio\.data"
set "HF_HOME=%VOICE_STUDIO_DATA_DIR%\models\cache"
set "VOICE_STUDIO_PORTABLE=1"
if not exist "runtime\python.exe" (
 echo Ban dang mo goi ma nguon, khong phai goi Windows Portable.
 echo Tai tep Voice-Studio-Windows-x64.zip trong GitHub Releases.
 pause
 exit /b 1
)
"runtime\python.exe" "voice-studio\portable_launcher.py"
pause
