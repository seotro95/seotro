@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 goto fail
set "PYTHONUTF8=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
echo HMONG STUDIO - CAI VA MO BANG MOT FILE
echo Lan dau: tu cai thu vien va tai phan mo hinh con thieu.
echo Tu thu CUDA neu phat hien NVIDIA; neu chua dung duoc, giu lai CPU.
echo Cac lan sau: dung lai bo may va mo hinh da cai.
echo Giu cua so nay mo trong khi su dung Studio. Ctrl+C de dong.
call setup_env.bat --clone-launch-auto
if errorlevel 1 goto fail
exit /b 0
:fail
echo.
echo Chua mo duoc Studio. Xem loi va nhat ky ben tren.
echo Giu nguyen .data va cac mau giong; sua loi roi chay lai CHAY-STUDIO.bat.
pause
exit /b 1
