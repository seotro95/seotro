@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
    python install_windows.py %*
) else (
    py -3 install_windows.py %*
)
if errorlevel 1 goto fail
if /I not "%~1"=="--automatic" pause
exit /b 0
:fail
echo.
echo Cai dat chua hoan tat. Xem loi cu the o tren.
echo Tool can Python 3.11 hoac 3.12 Windows 64-bit.
if /I not "%~1"=="--automatic" pause
exit /b 1
