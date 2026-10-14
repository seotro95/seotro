@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
    python -m venv .venv
) else (
    py -3 -m venv .venv
)
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo.
echo Da cai xong. Dat ffmpeg.exe va ffprobe.exe canh khoi_dong.bat.
echo Chay khoi_dong.bat de mo Video Studio VN.
pause
exit /b 0
:fail
echo Cai dat that bai. Can Python 3.10+ va ket noi Internet.
pause
exit /b 1
