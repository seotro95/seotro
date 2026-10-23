@echo off
setlocal
cd /d "%~dp0"
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONUTF8=1"
set "VOICE_STUDIO_VARIANT=hmong"
if exist "..\MO_VOICE_STUDIO_HMONG.bat" goto portable
if exist ".venv-hmong\Scripts\python.exe" goto source
echo Chua co Python Hmong. Chay install_hmong.bat truoc hoac dung ZIP Windows day du.
exit /b 1
:portable
if "%~1"=="" goto portable_install
call "..\MO_VOICE_STUDIO_HMONG.bat" %*
exit /b %ERRORLEVEL%
:source
if "%~1"=="" goto source_install
".venv-hmong\Scripts\python.exe" hmong_launcher.py %*
exit /b %ERRORLEVEL%
:portable_install
call "..\MO_VOICE_STUDIO_HMONG.bat" --install-cuda
exit /b %ERRORLEVEL%
:source_install
".venv-hmong\Scripts\python.exe" hmong_launcher.py --install-cuda
exit /b %ERRORLEVEL%
