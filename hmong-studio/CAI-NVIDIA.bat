@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 goto fail
set "PYTHONUTF8=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
echo HMONG STUDIO - CAI VA MO BANG GPU NVIDIA
echo Chi dung khi may co GPU NVIDIA va driver ho tro CUDA 12.4.
echo Tao bo may GPU rieng, giu nguyen bo may cu va cac mau giong.
echo Mo hinh da tai dung duoc tai su dung. Toc do phu thuoc GPU va noi dung.
echo Cac lan sau chay CHAY-STUDIO.bat de dung lai bo may GPU da cai.
echo Giu cua so nay mo trong khi su dung Studio. Ctrl+C de dong.
call setup_env.bat --clone-launch-gpu
if errorlevel 1 goto fail
exit /b 0
:fail
echo.
echo Chua cai/mo duoc GPU. Xem loi va nhat ky ben tren.
echo Bo may cu va thu muc .data khong bi xoa.
echo Neu da cai CPU thanh cong, chay CHAY-STUDIO.bat de dung lai CPU.
pause
exit /b 1
