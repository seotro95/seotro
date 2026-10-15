@echo off
cd /d "%~dp0"
where ffmpeg >nul 2>&1
if errorlevel 1 (
 echo Can cai FFmpeg va them vao PATH truoc. Xem README.md.
 pause
 exit /b 1
)
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r requirements-qwen.txt
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto fail
echo Cai xong thu vien. Tai model bang: .venv\Scripts\python.exe prepare_models.py all
echo Sau khi tai model, chay start.bat.
pause
exit /b 0
:fail
echo Cai dat that bai. Kiem tra thong bao loi ben tren.
pause
exit /b 1
