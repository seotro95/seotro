@echo off
setlocal
cd /d "%~dp0"
if exist "AutoDocStudio.exe" (
 start "" "AutoDocStudio.exe"
 exit /b
)
if not exist ".venv\Scripts\python.exe" (
 echo Chay CAI_DAT.bat truoc.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 pause
