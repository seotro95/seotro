@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Voice Studio - Tai bo giong da ngon ngu
if not exist "runtime\python.exe" (
  echo Can dat tep nay trong thu muc Voice Studio Portable co runtime\python.exe.
  pause
  exit /b 1
)
echo Dang cai bo tao giong rieng cho cac mau quoc te, gom tieng Thai.
echo Lan dau can Internet va dung luong trong cho model.
"runtime\python.exe" -s -X utf8 "app\prepare_international.py"
set "VOICE_EXIT=%ERRORLEVEL%"
if not "%VOICE_EXIT%"=="0" echo Chua cai xong. Giu thong bao loi nay de duoc ho tro.
pause
exit /b %VOICE_EXIT%
