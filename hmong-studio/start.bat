@echo off
setlocal
cd /d "%~dp0"
call "%~dp0prepare_env.bat"
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install --only-binary=PyYAML -r requirements.txt
if errorlevel 1 goto fail
echo Hmong Studio: http://127.0.0.1:8090
.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8090
if errorlevel 1 goto fail
exit /b 0
:fail
echo Khong khoi dong duoc. Xem thong bao phia tren. Tool can Python 3.10-3.12 64-bit.
echo Neu dang dung Python 3.15, cai them Python 3.12 roi chay lai. Khong can go Python cu.
pause
exit /b 1
