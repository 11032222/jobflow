@echo off
title JobFlow One-Click Shutdown
echo Closing JobFlow windows and processes...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $me=(Get-CimInstance Win32_Process -Filter \"ProcessId=$PID\").ParentProcessId; Get-CimInstance Win32_Process | Where-Object { $_.Name -in 'node.exe','electron.exe','python.exe','cmd.exe' -and $_.CommandLine -like '*jobflow*' -and $_.ProcessId -ne $me } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in 8000,5174 } | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
echo Done. All JobFlow services stopped.
ping -n 4 127.0.0.1 >nul
exit /b