@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 goto fail
set "PYTHONUTF8=1"
set "HMONG_BENCH_PYTHON="
echo HMONG STUDIO - BENCHMARK THAT 1 / 5 / 15 / 30 / 60 PHUT
echo Dong Studio truoc khi do. Dung bo may da cai, khong cai them thu vien.
echo Khong them khoang lang/loop audio de gia toc do. Warm cache bao rieng.
for %%V in (3.12 3.11 3.10) do (
  py -%%V -c "import struct,sys;sys.exit(0 if sys.implementation.name=='cpython' and struct.calcsize('P')==8 else 1)" >nul 2>nul
  if not errorlevel 1 (
    set "HMONG_BENCH_PYTHON=py -%%V"
    goto selected
  )
)
python -c "import struct,sys;sys.exit(0 if sys.implementation.name=='cpython' and struct.calcsize('P')==8 and (3,10)<=sys.version_info[:2]<(3,13) else 1)" >nul 2>nul
if not errorlevel 1 (
  set "HMONG_BENCH_PYTHON=python"
  goto selected
)
for /d %%E in (.venv-clone-* .venv) do (
  "%%E\Scripts\python.exe" -c "import struct,sys;sys.exit(0 if sys.implementation.name=='cpython' and struct.calcsize('P')==8 and (3,10)<=sys.version_info[:2]<(3,13) else 1)" >nul 2>nul
  if not errorlevel 1 (
    set HMONG_BENCH_PYTHON="%%E\Scripts\python.exe"
    goto selected
  )
)
echo Can Python3.10-3.12 64-bit va bo may da cai bang CHAY-STUDIO.bat.
goto fail
:selected
%HMONG_BENCH_PYTHON% -X utf8 benchmark_ultra.py %*
if errorlevel 1 goto fail
pause
exit /b 0
:fail
echo.
echo Chua xac nhan du target. Xem report.json neu da bat dau; khong co ket qua gia.
pause
exit /b 1
