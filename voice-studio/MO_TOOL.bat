@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
rem Support updating an existing Windows Portable without changing its data.
if exist "..\runtime\python.exe" goto portable
call start.bat
exit /b
:portable
set "PATH=%~dp0..\runtime;%~dp0..\ffmpeg\bin;%PATH%"
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "VOICE_STUDIO_PORTABLE=1"
"..\runtime\python.exe" portable_launcher.py
set "VOICE_START_EXIT=%ERRORLEVEL%"
pause
exit /b %VOICE_START_EXIT%
