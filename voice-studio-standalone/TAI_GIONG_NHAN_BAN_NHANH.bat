@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" bootstrap.py --models vieneu_nano_clone
  goto result
)
py -3.12 -c "import sys; assert sys.version_info[:2] == (3,12) and sys.maxsize > 2**32" >nul 2>nul
if not errorlevel 1 (
  py -3.12 bootstrap.py --models vieneu_nano_clone
  goto result
)
python -c "import sys; assert sys.version_info[:2] == (3,12) and sys.maxsize > 2**32" >nul 2>nul
if not errorlevel 1 (
  python bootstrap.py --models vieneu_nano_clone
  goto result
)
echo Can cai Python 3.12 64-bit truoc.
echo Tai tai: https://www.python.org/downloads/windows/
echo Khi cai, chon Add python.exe to PATH, sau do mo lai tep nay.
pause
exit /b 1
:result
set "VOICE_EXIT=%ERRORLEVEL%"
if not "%VOICE_EXIT%"=="0" echo Thao tac that bai. Xem thong bao loi ben tren.
pause
exit /b %VOICE_EXIT%
