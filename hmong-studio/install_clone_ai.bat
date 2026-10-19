@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 1
set "PYTHONUTF8=1"
call setup_env.bat
if errorlevel 1 goto fail
set "PATH=%~dp0.data\tools\ffmpeg\bin;%PATH%"
echo.
echo Cai bo may nhan ban Hmong Trang mien phi, chay tren CPU.
echo Can ket noi mang de cai thu vien va tai mo hinh lan dau.
echo Dong cua so tool dang chay truoc khi cai.
echo.
echo [1/5] Kiem tra va cai FFmpeg co xac minh checksum...
.venv\Scripts\python.exe -X utf8 prepare_media_tools.py
if errorlevel 1 goto fail
echo.
echo [2/5] Cai PyTorch CPU tu nguon chinh thuc...
.venv\Scripts\python.exe -m pip install --no-input --only-binary=:all: "torch==2.6.0" "torchaudio==2.6.0" --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto fail
echo.
echo [3/5] Cai thu vien suy luan, khong cai bo huan luyen CUDA...
rem Only these two pinned pure-Python packages lack upstream wheels.
rem All native packages must use wheels; do not disable TLS or use build tools.
.venv\Scripts\python.exe -m pip install --no-input --only-binary=:all: --no-binary=antlr4-python3-runtime,openai-whisper -r requirements-cosy.txt
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip check
if errorlevel 1 goto fail
echo.
echo [4/5] Tai va kiem tra mo hinh Hmong Trang...
.venv\Scripts\python.exe -X utf8 prepare_clone_model.py
if errorlevel 1 goto fail
echo.
echo [5/5] Kiem tra cac thu vien AI...
.venv\Scripts\python.exe -c "import torch,torchaudio,onnxruntime,whisper,transformers,soundfile; from hyperpyyaml import load_hyperpyyaml; print('Thu vien AI san sang. Torch:',torch.__version__)"
if errorlevel 1 goto fail
echo.
echo Da cai thu vien va tai mo hinh. Chay start.bat de mo tool.
echo Chon mau Nam/Nu, nhap chu Hmong ngan roi bam Tao voice.
echo Lan tao dau tien can nap mo hinh; CPU co the xu ly cham.
echo Chi nghe voice moi tao xong moi danh gia duoc phat am va do giong.
pause
exit /b 0
:fail
echo.
echo Chua cai xong bo may nhan ban. Xem loi ben tren.
echo Khong can go Python cu; dung Python 3.10-3.12 64-bit, khuyen dung 3.12.
echo Neu tai mo hinh bi ngat, chay lai file nay de tiep tuc.
echo Khong tat xac minh TLS va khong thay checksum de bo qua loi.
pause
exit /b 1
