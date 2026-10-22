@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
if exist "..\runtime\python.exe" goto portable
if not exist ".venv\Scripts\python.exe" (
 call install.bat --no-pause
 if errorlevel 1 goto fail
)
echo Cai them Qwen va nhan ban quoc te. Can Internet va nhieu GB dung luong.
".venv\Scripts\python.exe" setup_local.py --international
if errorlevel 1 goto fail
goto done
:portable
set "PATH=%~dp0..\runtime;%~dp0..\ffmpeg\bin;%PATH%"
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
"..\runtime\python.exe" setup_local.py --international --portable
if errorlevel 1 goto fail
:done
pause
exit /b 0
:fail
echo Chua cai xong giong quoc te. Xem loi ben tren. Giong Viet van dung duoc.
pause
exit /b 1
