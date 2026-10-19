@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 1
set "PYTHONUTF8=1"
call setup_env.bat
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install --no-input --only-binary=:all: -r requirements.txt
if errorlevel 1 goto fail
echo Hmong Studio: http://127.0.0.1:8090
.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8090 --no-access-log
if errorlevel 1 goto fail
exit /b 0
:fail
echo Khong khoi dong duoc. Xem loi ben tren; dung Python 3.12 64-bit.
pause
exit /b 1
