@echo off
setlocal
cd /d "%~dp0app"
if not defined HMONG_STUDIO_DATA_DIR set "HMONG_STUDIO_DATA_DIR=%~dp0.data"
set "PYTHONUTF8=1"
echo Hmong Nhanh - Doc van ban bang giong Nam / Nu
call prepare_env.bat
if errorlevel 1 goto fail
.venv\Scripts\python.exe setup_runtime.py %*
if errorlevel 1 goto fail
.venv\Scripts\python.exe launch.py %*
if errorlevel 1 goto fail
exit /b 0
:fail
echo.
echo Chua mo duoc cong cu. Xem loi phia tren, du lieu cu khong bi xoa.
pause
exit /b 1
