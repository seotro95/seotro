@echo off
setlocal
cd /d "%~dp0"
call start.bat --setup %*
exit /b %ERRORLEVEL%
