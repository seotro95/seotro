@echo off
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 goto fail
where ffmpeg >nul 2>nul
if errorlevel 1 echo Can cai FFmpeg vao PATH. Xem README.md.
pause
exit /b 0
:fail
echo Cai dat that bai. Xem loi ben tren.
pause
exit /b 1
