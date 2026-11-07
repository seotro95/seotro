@echo off
setlocal
cd /d "%~dp0"
where node.exe >nul 2>nul
if not errorlevel 1 (
  node.exe "%~dp0silence_clips.mjs"
  goto done
)
set "SIBERIA_MUSE_EXE="
for /f "usebackq delims=" %%I in (`powershell.exe -NoProfile -Command "Get-Process -Name '*Muse*' -ErrorAction SilentlyContinue ^| Where-Object { $_.Path -and $_.Path -notmatch 'crashpad' } ^| Select-Object -First 1 -ExpandProperty Path"`) do set "SIBERIA_MUSE_EXE=%%I"
if not defined SIBERIA_MUSE_EXE (
  echo Open Muse AI Studio first, or install Node.js 22 or newer from https://nodejs.org/en/download
  goto done
)
set "ELECTRON_RUN_AS_NODE=1"
"%SIBERIA_MUSE_EXE%" "%~dp0silence_clips.mjs"
:done
pause
