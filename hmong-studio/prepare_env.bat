@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 goto use_py
where python >nul 2>nul
if not errorlevel 1 goto use_python
echo Khong tim thay Python. Hay cai Python 3.12 64-bit va bat Python Launcher.
echo https://www.python.org/downloads/windows/
exit /b 1
:use_py
py bootstrap.py
exit /b %errorlevel%
:use_python
python bootstrap.py
exit /b %errorlevel%
