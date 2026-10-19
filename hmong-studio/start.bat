@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 1
set "PYTHONUTF8=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PATH=%~dp0.data\tools\ffmpeg\bin;%PATH%"
call setup_env.bat --clone-start
if errorlevel 1 goto fail
exit /b 0
:fail
echo Chua mo duoc Studio. Hay cai xong bang install_clone_ai.bat truoc.
echo Neu Studio cu con mo, dong cua so do roi chay lai start.bat.
pause
exit /b 1
