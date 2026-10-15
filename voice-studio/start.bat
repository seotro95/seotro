@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Chay install.bat truoc.
 pause
 exit /b 1
)
echo Voice Studio: mo trinh duyet tai http://127.0.0.1:8770
".venv\Scripts\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8770 --no-access-log
pause
