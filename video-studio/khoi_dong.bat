@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Hay chay cai_dat.bat truoc.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" launcher.py
pause
