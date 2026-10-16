@echo off
cd /d "%~dp0"
set "PY=.venv\Scripts\python.exe"
if exist "..\runtime\python.exe" set "PY=..\runtime\python.exe"
"%PY%" prepare_subtitles.py
pause
