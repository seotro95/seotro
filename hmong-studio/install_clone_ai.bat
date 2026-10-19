@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 1
set "PYTHONUTF8=1"
echo Bo cai NHAN BAN GIONG - moi truong rieng, khong cai de .venv cu.
echo Can Internet lan dau de tai thu vien va khoang 5.4 GB mo hinh.
echo Dong cac cua so Studio/bo cai cua tool truoc khi bat dau.
call setup_env.bat --clone-install
if errorlevel 1 goto fail
echo Chay start.bat, chon Nam/Nu va bam Tao voice. Khong can micro.
pause
exit /b 0
:fail
echo Chua cai xong. Xem loi va duong dan nhat ky ben tren.
echo Khong xoa .data hoac cac mau giong. Khong can go Python hay cai Visual C++ Build Tools.
pause
exit /b 1
