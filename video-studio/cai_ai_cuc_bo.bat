@echo off
chcp 65001 >nul
cd /d "%~dp0"
call cai_dat.bat
exit /b %errorlevel%
