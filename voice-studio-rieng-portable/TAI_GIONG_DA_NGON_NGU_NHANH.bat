@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Voice Studio - Tai bo giong da ngon ngu native
if not exist "runtime\python.exe" (
  echo Can dat tep nay trong thu muc Voice Studio Portable co runtime\python.exe.
  pause
  exit /b 1
)
echo Dang tai bo doc OmniVoice native tuy chon. Lan dau can Internet va 1,6 GB trong.
echo Bo nhan loi mau giong chay ngoai tuyen; khong gui tep giong len mang.
echo Giu nguyen giọng mau da cai; am sac co the khac khi doi mo hinh.
"runtime\python.exe" -s -X utf8 "app\prepare_native.py"
set "VOICE_EXIT=%ERRORLEVEL%"
if not "%VOICE_EXIT%"=="0" echo Chua cai xong. Giu thong bao loi nay de duoc ho tro.
pause
exit /b %VOICE_EXIT%
