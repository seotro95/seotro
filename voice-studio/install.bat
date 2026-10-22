@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
if exist ".venv\Scripts\python.exe" (
 ".venv\Scripts\python.exe" setup_local.py
 goto result
)
py -3.12 -c "import sys" >nul 2>&1
if not errorlevel 1 (
 py -3.12 setup_local.py
 goto result
)
python -c "import sys" >nul 2>&1
if errorlevel 1 (
 echo Can cai Python 3.12 64-bit tu https://www.python.org/downloads/windows/
 echo Bat Add python.exe to PATH, mo lai cua so roi chay MO_TOOL.bat.
 if /I not "%~1"=="--no-pause" pause
 exit /b 1
)
python setup_local.py
:result
set "VOICE_SETUP_EXIT=%ERRORLEVEL%"
if not "%VOICE_SETUP_EXIT%"=="0" echo Cai dat chua hoan tat. Xem loi ben tren va chay lai.
if /I not "%~1"=="--no-pause" pause
exit /b %VOICE_SETUP_EXIT%
