@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
echo HMONG STUDIO - THONG TIN GPU TREN MAY NAY
echo Lenh nay chi doc thong tin, khong cai hay thay doi driver.
echo.
powershell.exe -NoProfile -Command "Get-CimInstance Win32_VideoController -ErrorAction Stop | ForEach-Object { Write-Output ('GPU: ' + $_.Name) }; if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) { Write-Output 'NVIDIA: ten card, VRAM, driver'; nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader } else { Write-Output 'Khong tim thay nvidia-smi. Ten GPU o tren giup kiem tra kha nang tang toc.' }"
if errorlevel 1 echo Khong doc duoc thong tin. Mo dxdiag, chon Display/Hien thi de xem ten GPU.
echo.
echo Can ten card va VRAM de chon cach tang toc phu hop.
echo DirectX 12 chi la phien ban phan mem, khong phai ten GPU.
pause
exit /b 0
