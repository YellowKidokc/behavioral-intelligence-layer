@echo off
setlocal
title FAP Postgres Sync
echo ============================================
echo  SYNC: FAP Local Logs To Postgres
echo ============================================

set PYTHON_EXE=
if exist "C:\Users\lowes\AppData\Local\Programs\Python\Python313\python.exe" set PYTHON_EXE=C:\Users\lowes\AppData\Local\Programs\Python\Python313\python.exe
if not defined PYTHON_EXE if exist "C:\Users\lowes\AppData\Local\Programs\Python\Python312\python.exe" set PYTHON_EXE=C:\Users\lowes\AppData\Local\Programs\Python\Python312\python.exe
if not defined PYTHON_EXE set PYTHON_EXE=py -3

cd /d D:\BIL
%PYTHON_EXE% "D:\BIL\engines\pipeline\fap_postgres_sync.py"
set RC=%ERRORLEVEL%

echo ============================================
echo  Done (rc=%RC%).
echo  Report: D:\BIL\data\fap_sync\FAP_POSTGRES_SYNC.latest.json
echo ============================================
pause
exit /b %RC%
 
