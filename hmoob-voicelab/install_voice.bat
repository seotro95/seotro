@echo off
setlocal
cd /d "%~dp0"
echo Hmoob VoiceLab - Cai engine giong Hmong cuc bo
echo Can Python 3.10-3.12 64-bit va FFmpeg. Khong can API key.
set "HMOOB_PYTHON="
for %%V in (3.12 3.11 3.10) do (
  if not defined HMOOB_PYTHON (
    py -%%V -c "import struct; raise SystemExit(0 if struct.calcsize('P') == 8 else 1)" >nul 2>&1
    if not errorlevel 1 set "HMOOB_PYTHON=py -%%V"
  )
)
if not defined HMOOB_PYTHON (
  echo Chua tim thay Python 3.10-3.12 64-bit. Cai Python 3.12 tu python.org va Python Launcher.
  exit /b 1
)
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -c "import sys,struct; raise SystemExit(0 if sys.version_info.major == 3 and sys.version_info.minor in (10,11,12) and struct.calcsize('P') == 8 else 1)"
  if errorlevel 1 (
    echo .venv khong tuong thich. Giu nguyen du lieu; doi ten thu muc nay truoc khi cai lai.
    exit /b 1
  )
) else (
  %HMOOB_PYTHON% -m venv .venv
  if errorlevel 1 exit /b 1
)
.venv\Scripts\python.exe -m pip install "torch==2.8.0+cpu" "torchaudio==2.8.0+cpu" --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m pip install -r requirements-voice.txt
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe setup_voice.py
if errorlevel 1 exit /b 1
echo Da cai va xac minh tep. Chay start.bat, nhap loi khop doan mau va tao thu mot cau.
echo Ban CPU duoc cai mac dinh. Muon dung NVIDIA, xem huong dan PyTorch CUDA trong README.
exit /b 0
