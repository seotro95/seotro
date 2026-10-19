@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 1
set "PYTHONUTF8=1"
set "HMONG_SETUP_PYTHON="
rem A working existing venv does not require a globally registered Python.
.venv\Scripts\python.exe -c "import struct,sys;sys.exit(0 if sys.implementation.name=='cpython' and struct.calcsize('P')==8 and (3,10)<=sys.version_info[:2]<(3,13) else 1)" >nul 2>nul
if not errorlevel 1 (
  set "HMONG_SETUP_PYTHON=.venv\Scripts\python.exe"
  goto selected
)
rem Prefer Python 3.12; never create the environment using Python 3.13+.
for %%V in (3.12 3.11 3.10) do (
  py -%%V -c "import struct,sys;sys.exit(0 if sys.implementation.name=='cpython' and struct.calcsize('P')==8 and (3,10)<=sys.version_info[:2]<(3,13) else 1)" >nul 2>nul
  if not errorlevel 1 (
    set "HMONG_SETUP_PYTHON=py -%%V"
    goto selected
  )
)
python -c "import struct,sys;sys.exit(0 if sys.implementation.name=='cpython' and struct.calcsize('P')==8 and (3,10)<=sys.version_info[:2]<(3,13) else 1)" >nul 2>nul
if not errorlevel 1 (
  set "HMONG_SETUP_PYTHON=python"
  goto selected
)
echo.
echo Khong tim thay Python 3.10-3.12 64-bit. Khuyen dung Python 3.12 64-bit.
echo Python 3.15 trong anh loi chua duoc ho tro bo cai nay.
echo Tai Python 3.12.10 Windows installer 64-bit tu trang chinh thuc:
echo https://www.python.org/downloads/release/python-31210/
echo Khi cai, chon Python Launcher va Add python.exe to PATH.
echo Khong can go Python cu. Cai xong hay chay lai start.bat.
exit /b 1
:selected
%HMONG_SETUP_PYTHON% -X utf8 setup_venv.py
exit /b %errorlevel%
