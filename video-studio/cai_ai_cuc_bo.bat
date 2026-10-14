@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Hay chay cai_dat.bat truoc.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements-ai-local.txt
if errorlevel 1 (
    echo Cai AI cuc bo that bai. Kiem tra Python 64-bit va Internet.
    pause
    exit /b 1
)
echo Da cai engine dich, Whisper CPU va Piper TTS. Khoi dong lai tool.
pause
