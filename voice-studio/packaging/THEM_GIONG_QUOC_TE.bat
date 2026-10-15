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
echo Can Internet va vai GB dung luong. Dong Voice Studio truoc khi tiep tuc.
choice /C YN /M "Tai them model Anh, Nhat, Han va nhan ban quoc te?"
if errorlevel 2 exit /b 0
"runtime\python.exe" -m pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto fail
"runtime\python.exe" -m pip install -r "voice-studio\requirements-qwen.txt"
if errorlevel 1 goto fail
"runtime\python.exe" -m pip check
if errorlevel 1 goto fail
"runtime\python.exe" "voice-studio\prepare_models.py" qwen
if errorlevel 1 goto fail
"runtime\python.exe" "voice-studio\prepare_models.py" qwen_clone
if errorlevel 1 goto fail
echo Da tai xong. Mo lai MO_VOICE_STUDIO.bat.
pause
exit /b 0
:fail
echo Tai chua hoan tat. Kiem tra loi ben tren va ket noi Internet, roi chay lai.
pause
exit /b 1
