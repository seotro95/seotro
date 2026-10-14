@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    call cai_dat.bat --automatic
    if errorlevel 1 exit /b 1
)
echo Dong cua so tool cu truoc khi cap nhat.
".venv\Scripts\python.exe" launcher.py --update-only --no-browser
if errorlevel 1 (
    echo Chua cap nhat duoc. Kiem tra Internet va dong tool cu.
    pause
    exit /b 1
)
echo Mo khoi_dong.bat de dung tool.
pause
