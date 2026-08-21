@echo off
REM Isolated Chrome with CDP 9222. Profile lives next to this script (do NOT use D:\ — that disk may not exist).
set SCRIPT_DIR=%~dp0
set PROFILE=%SCRIPT_DIR%..\..\auto-zhipin\chrome_profile
if not exist "%PROFILE%" mkdir "%PROFILE%"
set CHROME=
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe
if "%CHROME%"=="" (
  echo 未找到 chrome.exe，请先安装 Google Chrome。
  pause
  exit /b 1
)
start "" "%CHROME%" --remote-debugging-port=9222 --user-data-dir="%PROFILE%" --disable-blink-features=AutomationControlled "https://www.zhipin.com/web/user/?ka=header-login"
echo 已启动调试 Chrome。请在弹出窗口登录 BOSS 直聘，再回到 JobFlow 采集。


