@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  python -m venv .venv
  if errorlevel 1 goto fail
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo Hmong Studio: http://127.0.0.1:8090
.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8090
if errorlevel 1 goto fail
exit /b 0
:fail
echo Khong khoi dong duoc. Kiem tra Python 3.10+ va ket noi mang.
pause
exit /b 1
