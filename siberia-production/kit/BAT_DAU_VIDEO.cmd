@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "SIBERIA_RUNTIME="
for /f "delims=" %%P in ('where node.exe 2^>nul') do if not defined SIBERIA_RUNTIME set "SIBERIA_RUNTIME=%%P"
if not defined SIBERIA_RUNTIME for /f "delims=" %%P in ('powershell.exe -NoProfile -NonInteractive -Command "$p=@(Get-Process -Name 'Muse AI Studio' -ErrorAction SilentlyContinue); if($p.Count -gt 0){$p[0].Path}"') do set "SIBERIA_RUNTIME=%%P"
if not defined SIBERIA_RUNTIME (
  echo Mo Muse AI Studio 1.6.0 truoc, dang nhap Muse 01, roi chay lai tep nay.
  pause
  exit /b 1
)
set "ELECTRON_RUN_AS_NODE=1"
set "SIBERIA_OPERATION=all"
if not "%~1"=="" set "SIBERIA_OPERATION=%~1"
"%SIBERIA_RUNTIME%" "%~dp0launch.mjs" %SIBERIA_OPERATION% %2 %3 %4 %5 %6 %7 %8 %9
if errorlevel 1 (
 echo Da dung. Ket qua da tao van duoc giu. Xem README_VI.md de tiep tuc.
) else (
 echo Hoan tat. Kiem tra tep MP4 va FINAL_REPORT.json trong thu muc nay.
)
pause
