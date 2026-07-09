@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD=python"
if not "%PYTHON%"=="" set "PYTHON_CMD=%PYTHON%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verify.ps1"
exit /b %ERRORLEVEL%
