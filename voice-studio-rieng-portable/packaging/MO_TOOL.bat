@echo off
setlocal
title Voice Studio Rieng 1.5.0 Portable
cd /d "%~dp0"
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONUTF8=1"
set "VOICE_STUDIO_DATA_DIR=%~dp0app\.data"
set "HF_HOME=%~dp0app\.data\models\cache"
set "HF_HUB_CACHE=%~dp0app\.data\models\cache\hub"
set "HUGGINGFACE_HUB_CACHE=%HF_HUB_CACHE%"
set "HF_HUB_OFFLINE=1"
set "TRANSFORMERS_OFFLINE=1"
set "HF_HUB_DISABLE_TELEMETRY=1"
set "GRADIO_ANALYTICS_ENABLED=False"
set "DO_NOT_TRACK=1"
set "PATH=%~dp0ffmpeg\bin;%~dp0runtime;%PATH%"
if not exist "%~dp0runtime\python.exe" goto incomplete
if not exist "%~dp0ffmpeg\bin\ffmpeg.exe" goto incomplete
if not exist "%~dp0app\.data\models\vieneu_nano.ready" goto incomplete
"%~dp0runtime\python.exe" -s -X utf8 "%~dp0app\launcher.py" %*
set "VOICE_EXIT=%ERRORLEVEL%"
if "%VOICE_EXIT%"=="0" exit /b 0
echo Khong mo duoc Voice Studio. Hay giu nguyen thu muc va xem loi ben tren.
pause
exit /b %VOICE_EXIT%
:incomplete
echo Goi Portable chua duoc giai nen day du. Hay giai nen TOAN BO ZIP vao thu muc moi.
echo Khong can cai Python hoac tai model. Goi day du phai co runtime, ffmpeg va app.
pause
exit /b 1
