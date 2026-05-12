@echo off
setlocal
title FAP Healthcheck
echo ============================================
echo  HEALTHCHECK: Folder Automations & Pipelines
echo ============================================

set PYTHON_EXE=
if exist "C:\Users\lowes\AppData\Local\Programs\Python\Python313\python.exe" set PYTHON_EXE=C:\Users\lowes\AppData\Local\Programs\Python\Python313\python.exe
if not defined PYTHON_EXE if exist "C:\Users\lowes\AppData\Local\Programs\Python\Python312\python.exe" set PYTHON_EXE=C:\Users\lowes\AppData\Local\Programs\Python\Python312\python.exe
if not defined PYTHON_EXE set PYTHON_EXE=py -3

cd /d D:\BIL
%PYTHON_EXE% "D:\BIL\engines\pipeline\fap_healthcheck.py"
set RC=%ERRORLEVEL%

echo ============================================
echo  Done (rc=%RC%).
echo  Report: D:\BIL\data\fap_health\FAP_HEALTH.latest.md
echo ============================================
pause
exit /b %RC%
