@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
echo Starting kagent...
set "PY_CMD="
if exist ".venv\Scripts\python.exe" set "PY_CMD=.venv\Scripts\python.exe"
if not defined PY_CMD where py >nul 2>nul && set "PY_CMD=py -3"
if not defined PY_CMD where python >nul 2>nul && set "PY_CMD=python"

if not defined PY_CMD (
    echo Python launcher not found.
    echo Install Python 3.10+ and make sure py or python is available in PATH.
    echo.
    pause
    exit /b 1
)

call %PY_CMD% main.py
echo.
echo === kagent exited with code %errorlevel% ===
echo Check crash.log for details.
pause
