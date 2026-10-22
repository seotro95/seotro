@echo off
cd /d "%~dp0"
set "PYTHONUTF8=1"
if not exist ".venv\Scripts\python.exe" (
 echo Chay install.bat truoc.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" portable_launcher.py
if errorlevel 1 (
 echo Khong mo duoc Voice Studio. Xem loi ben tren.
 pause
 exit /b 1
)
