@echo off
chcp 65001 >nul
cd /d "%~dp0"
call cai_dat.bat --automatic --ensure
if errorlevel 1 (
    pause
    exit /b 1
)
".venv\Scripts\python.exe" launcher.py
pause
