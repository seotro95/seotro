@echo off
setlocal
set "MELO_VIET_PACKAGE=%~dp0"
set "MELO_VIET_ACTION=install-fast"
powershell.exe -NoLogo -NoProfile -Command "$ErrorActionPreference='Stop'; & ([ScriptBlock]::Create([IO.File]::ReadAllText((Join-Path $env:MELO_VIET_PACKAGE 'bootstrap.ps1'))))"
set "MELO_EXIT=%ERRORLEVEL%"
if not "%MELO_EXIT%"=="0" pause
exit /b %MELO_EXIT%
