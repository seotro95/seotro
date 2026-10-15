@echo off
setlocal
cd /d "%~dp0"
set "OLLAMA_NO_CLOUD=1"
set "WRITER_MODEL=%~1"
if not defined WRITER_MODEL set "WRITER_MODEL=qwen3:4b"
set "OLLAMA_RUNNER=ollama"
where ollama >nul 2>&1
if errorlevel 1 (
 if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
  set "OLLAMA_RUNNER=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
 ) else (
  echo Can cai Ollama truoc tu https://ollama.com/download/windows
  echo Cai xong, mo Ollama va chay lai tep nay. Khong can tai khoan hay API key.
  pause
  exit /b 1
 )
)
echo Dang tai model %WRITER_MODEL%. Chi can Internet khi tai model.
echo May it RAM co the dung: setup_local_writer.bat qwen3:1.7b
"%OLLAMA_RUNNER%" pull "%WRITER_MODEL%"
if errorlevel 1 (
 echo Chua tai duoc model. Mo Ollama, kiem tra mang va dung luong dia, roi thu lai.
 pause
 exit /b 1
)
echo Da san sang. Chay start.bat, mo AI viet kich ban, chon Ollama.
echo Ten model can chon: %WRITER_MODEL%
pause
