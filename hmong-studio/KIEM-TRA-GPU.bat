@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
call setup_env.bat --gpu-info
if errorlevel 1 echo Khong doc duoc thong tin. Mo dxdiag, chon Display/Hien thi de xem ten GPU.
pause
exit /b 0
