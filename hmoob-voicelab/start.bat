@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" launch.py %*
) else (
  py -3.12 launch.py %*
)
if errorlevel 1 (
  echo Khong mo duoc tool. Can Python 3.12 64-bit; xem README.md.
  pause
)
