@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Chay install.bat truoc.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" prepare_models.py vieneu_fast
if errorlevel 1 (
 echo CPU co the khong ho tro VNNI hoac tai model that bai. Van dung duoc che do Tieu chuan.
 pause
 exit /b 1
)
echo Da san sang che do Nhanh cho tieng Viet.
pause
