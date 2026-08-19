@echo off
REM Start debug Chrome with fixed CDP port 9222 and isolated profile (persistent login)
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=D:\zhipin_chrome_profile --disable-blink-features=AutomationControlled about:blank

