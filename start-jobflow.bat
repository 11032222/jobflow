@echo off
title JobFlow One-Click Launcher
cd /d "%~dp0"

set "API_DIR=%~dp0api"
set "WEB_DIR=%~dp0web"
set "PY=%API_DIR%\.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo [ERROR] 未找到后端虚拟环境: %PY%
  echo 请先在 api 目录执行: py -3.11 -m venv .venv ^&^& .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)

rem --- Backend: skip if already running ---
powershell -NoProfile -Command "try{$r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/docs' -UseBasicParsing -TimeoutSec 2; exit 0}catch{exit 1}" >nul 2>&1
if not errorlevel 1 goto backend_already
echo [1/3] Starting backend API (port 8000) ...
start "JobFlow-API" cmd /k "cd /d "%API_DIR%" && "%PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
goto check_front

:backend_already
echo Backend already running on port 8000, skipping.

rem --- Frontend: skip if already running ---
:check_front
powershell -NoProfile -Command "try{$r=Invoke-WebRequest -Uri 'http://localhost:5174/' -UseBasicParsing -TimeoutSec 2; exit 0}catch{exit 1}" >nul 2>&1
if not errorlevel 1 goto frontend_already
echo [2/3] Starting frontend dev server (port 5174) ...
start "JobFlow-Vite" cmd /k "cd /d "%WEB_DIR%" && npm run dev"

echo Waiting for services to be ready ...
powershell -NoProfile -Command "function Test-Port($p){try{$c=New-Object Net.Sockets.TcpClient;$ar=$c.BeginConnect('127.0.0.1',$p,$null,$null);$ok=$ar.AsyncWaitHandle.WaitOne(1000)-and $c.Connected;$c.Close();return $ok}catch{return $false}};$t=0;do{$ok=(Test-Port 5174)-and(Test-Port 8000);if($ok){exit 0};Start-Sleep -Milliseconds 600;$t++}while($t -lt 60);exit 1"
if errorlevel 1 echo Frontend did not respond in time, opening desktop anyway...
goto open_desktop

:frontend_already
echo Frontend already running on port 5174, skipping.

:open_desktop
echo [3/3] Opening JobFlow desktop window ...
start "JobFlow-Desktop" cmd /k "cd /d "%WEB_DIR%" && npm run electron:dev"

echo.
echo ============================================
echo  JobFlow is starting. Login: admin / 123456
echo  Browser: http://localhost:5174
echo  API docs: http://127.0.0.1:8000/docs
echo  Close the 3 JobFlow windows to stop it.
echo ============================================
ping -n 6 127.0.0.1 >nul
exit /b
