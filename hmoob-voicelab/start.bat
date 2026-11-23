@echo off
setlocal
title Hmoob VoiceLab
echo Hmoob VoiceLab - dang khoi dong. Giu cua so nay mo. 1>&2
cd /d "%~dp0"
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONUTF8=1"
set "HMOOB_BOOT_PYTHON="
for %%P in ("runtime\python.exe" "python\python.exe" "..\runtime\python.exe" "..\python\python.exe" ".venv\Scripts\python.exe") do (
  if not defined HMOOB_BOOT_PYTHON if exist "%%~P" set "HMOOB_BOOT_PYTHON=%%~fP"
)
if defined HMOOB_BOOT_PYTHON goto run_tool
for %%V in (3.12 3.11 3.10) do (
  if not defined HMOOB_BOOT_PYTHON (
    py -%%V -c "import struct; raise SystemExit(0 if struct.calcsize('P') == 8 else 1)" >nul 2>&1
    if not errorlevel 1 set "HMOOB_BOOT_PYTHON=py -%%V"
  )
)
if defined HMOOB_BOOT_PYTHON goto run_system
python -c "import sys,struct; raise SystemExit(0 if sys.version_info.major == 3 and sys.version_info.minor in (10,11,12) and struct.calcsize('P') == 8 else 1)" >nul 2>&1
if not errorlevel 1 (
  set "HMOOB_BOOT_PYTHON=python"
  goto run_system
)
echo Chua tim thay Python 3.10-3.12 64-bit.
echo Dung ban Portable day du, hoac cai Python 3.12 64-bit tu python.org.
pause
exit /b 1
:run_tool
"%HMOOB_BOOT_PYTHON%" bootstrap.py %*
goto finished
:run_system
%HMOOB_BOOT_PYTHON% bootstrap.py %*
:finished
set "HMOOB_EXIT=%ERRORLEVEL%"
if not "%HMOOB_EXIT%"=="0" pause
exit /b %HMOOB_EXIT%
