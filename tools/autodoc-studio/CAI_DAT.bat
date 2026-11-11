@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
 echo Can Python3.12 64-bit. Tai tu https://www.python.org/downloads/windows/
 echo Chon Add Python to PATH khi cai. Ban Windows portable khong can buoc nay.
 pause
 exit /b 1
)
py -3.12 -m venv .venv
if errorlevel 1 (
 echo Can Python3.12 64-bit. Vui long cai Python roi chay lai.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" main.py --doctor
if errorlevel 1 (
 echo Can ffmpeg.exe va ffprobe.exe trong thu muc bin hoac PATH.
 echo Tool tu tai FFmpeg lan dau; kiem tra ket noi mang.
 pause
 exit /b 1
)
echo Da cai xong. Chay MO_TOOL.bat.
pause
exit /b 0
:failed
echo Cai dat chua hoan tat. Kiem tra mang va loi ben tren.
pause
exit /b 1
