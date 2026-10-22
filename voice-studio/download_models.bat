@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Chay install.bat truoc.
 pause
 exit /b 1
)
echo Dang tai model tieng Viet: Nano nhanh, nhan ban va Turbo. Can Internet.
".venv\Scripts\python.exe" prepare_models.py vi
if errorlevel 1 (
 echo Tai mo hinh chua hoan tat. Kiem tra loi ben tren va ket noi mang.
 pause
 exit /b 1
)
echo Da tai xong. Chay start.bat de mo Voice Studio.
pause
