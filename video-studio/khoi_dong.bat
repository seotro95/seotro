@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    call cai_dat.bat --automatic
    if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" launcher.py
pause
