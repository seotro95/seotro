@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "VOICE_WITH_QWEN=0"
set "VOICE_PREPARE_MODELS=1"
:args
if "%~1"=="" goto prerequisites
if /i "%~1"=="--qwen" (
 set "VOICE_WITH_QWEN=1"
 shift
 goto args
)
if /i "%~1"=="--no-models" (
 set "VOICE_PREPARE_MODELS=0"
 shift
 goto args
)
echo Tuy chon khong hop le. Dung: install.bat [--qwen] [--no-models]
exit /b 2
:prerequisites
where ffmpeg >nul 2>&1
if errorlevel 1 (
 echo Can cai FFmpeg va them vao PATH truoc. Xem README.md.
 goto fail
)
where ffprobe >nul 2>&1
if errorlevel 1 (
 echo Can cai ffprobe cung FFmpeg va them vao PATH.
 goto fail
)
if not exist ".venv\Scripts\python.exe" (
 py -3.12 -m venv .venv
 if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -c "import sys; assert (3,10) <= sys.version_info[:2] < (3,13), 'Can Python 3.10-3.12. Sao luu .venv va tao lai bang Python 3.12; khong xoa .data.'"
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
if "%VOICE_WITH_QWEN%"=="1" (
 ".venv\Scripts\python.exe" -m pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
 if errorlevel 1 goto fail
 ".venv\Scripts\python.exe" -m pip install -r requirements-qwen.txt
 if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto fail
if "%VOICE_PREPARE_MODELS%"=="1" (
 ".venv\Scripts\python.exe" prepare_models.py vieneu_nano
 if errorlevel 1 goto fail
 ".venv\Scripts\python.exe" prepare_models.py vieneu
 if errorlevel 1 goto fail
 if "%VOICE_WITH_QWEN%"=="1" (
  ".venv\Scripts\python.exe" prepare_models.py qwen
  if errorlevel 1 goto fail
  ".venv\Scripts\python.exe" prepare_models.py qwen_clone
  if errorlevel 1 goto fail
 )
)
echo Cai xong. Chay start.bat. Giong quoc te tuy chon: install.bat --qwen
pause
exit /b 0
:fail
echo Cai dat that bai. Kiem tra thong bao loi ben tren. Du lieu .data duoc giu nguyen.
pause
exit /b 1
