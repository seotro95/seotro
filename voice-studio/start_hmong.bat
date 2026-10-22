@echo off
cd /d "%~dp0"
if not exist ".venv-hmong\Scripts\python.exe" (
 echo Can cai moi truong Hmong hoac dung goi Windows day du.
 pause
 exit /b 1
)
".venv-hmong\Scripts\python.exe" hmong_launcher.py %*
if errorlevel 1 pause
