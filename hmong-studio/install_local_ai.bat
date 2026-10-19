@echo off
cd /d "%~dp0"
if errorlevel 1 exit /b 1
echo File nay se mo bo cai NHAN BAN moi. MMS/ASR rieng: install_mms_asr.bat.
call install_clone_ai.bat
exit /b %errorlevel%
