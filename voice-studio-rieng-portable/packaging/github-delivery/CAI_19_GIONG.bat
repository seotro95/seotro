@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Voice Studio - Cai 19 giong mac dinh
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONUTF8=1"
powershell.exe -NoLogo -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0install_secure_voices.ps1" %*
set "VOICE_INSTALL_EXIT=%ERRORLEVEL%"
echo.
pause
exit /b %VOICE_INSTALL_EXIT%
