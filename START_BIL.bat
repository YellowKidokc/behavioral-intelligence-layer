@echo off
echo === BIL - Behavioral Intelligence Layer ===
echo.

echo Starting BIL preference engine...
start "BIL Server" cmd /k "cd /d D:\BIL\behavioral-intelligence-layer-OBS-Plugin-Final-Claude && python -m bil.bil_server"
timeout /t 2 >nul

echo Starting BIL service (tray + capture + watcher)...
start "BIL Service" cmd /k "cd /d D:\BIL && python bil_service.py"

echo.
echo BIL is running.
echo   Preference engine: http://localhost:8420
echo   Hotkey:            Ctrl+Alt+Shift+P
echo   Watcher:           every 5 minutes
echo   Tray icon:         bottom-right
echo.
