@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 goto fail
set "PYTHONUTF8=1"
echo HMONG STUDIO - DO VA CHON CAU HINH GPU TREN MAY NAY
echo Dong Studio truoc khi do. Khong cai lai thu vien hoac tai lai mo hinh.
echo Do FP32/FP16 bang mau ngan, Review va Loc on Nhe; giu WAV de nghe so sanh.
echo Ket qua mau ngan KHONG xac nhan tao 1 gio voice trong 2 phut.
call setup_env.bat --clone-benchmark
if errorlevel 1 goto fail
echo Da xong. Chay CHAY-STUDIO.bat de dung cau hinh da do.
pause
exit /b 0
:fail
echo.
echo Chua luu cau hinh toc do moi. Xem loi ben tren; cau hinh cu duoc giu nguyen.
pause
exit /b 1
