@echo off
setlocal
title Install FAP Postgres Sync Tasks
echo ============================================
echo  INSTALL: FAP Postgres Sync Tasks
echo ============================================
echo Creates two scheduled tasks: 7:45 AM and 7:45 PM.
echo.

set BAT=D:\BIL\RUN_FAP_POSTGRES_SYNC.bat

schtasks /Create /TN "FAP Postgres Sync AM" /TR "\"%BAT%\"" /SC DAILY /ST 07:45 /F
set RC1=%ERRORLEVEL%
schtasks /Create /TN "FAP Postgres Sync PM" /TR "\"%BAT%\"" /SC DAILY /ST 19:45 /F
set RC2=%ERRORLEVEL%

echo ============================================
echo  Done (am=%RC1%, pm=%RC2%).
echo ============================================
pause
if not "%RC1%"=="0" exit /b %RC1%
exit /b %RC2%
