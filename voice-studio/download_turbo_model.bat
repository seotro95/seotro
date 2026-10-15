@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Chay install.bat truoc.
 pause
 exit /b 1
)
echo Tai giong Nano sieu nhanh. Chat luong thap hon Turbo, uu tien tieng Viet.
".venv\Scripts\python.exe" prepare_models.py vieneu_nano
if errorlevel 1 (
 echo Tai model that bai. Kiem tra loi ben tren va ket noi Internet.
 pause
 exit /b 1
)
echo Mo lai Voice Studio, chon Minh Quan hoac Ai Han co chu Sieu nhanh.
pause
