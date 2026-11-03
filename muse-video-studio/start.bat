@echo off
setlocal
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 goto missingnode
node -e "if(Number(process.versions.node.split('.')[0])<24)process.exit(1)"
if errorlevel 1 goto missingnode
if exist node_modules\react\package.json goto build
call npm ci
if errorlevel 1 goto failed
:build
if exist dist\index.html goto launch
call npm run build
if errorlevel 1 goto failed
:launch
echo Open http://127.0.0.1:8788 after the server is ready. Ctrl+C to stop.
call npm start
if errorlevel 1 goto failed
exit /b 0
:missingnode
echo Install Node.js 24 LTS from https://nodejs.org/ then run start.bat again.
pause
exit /b 1
:failed
echo Startup failed. Read the error above. Your projects have not been deleted.
pause
exit /b 1
