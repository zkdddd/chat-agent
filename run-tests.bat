@echo off
setlocal
cd /d "%~dp0"

if "%PYTHON%"=="" (
    if exist ".venv\Scripts\python.exe" (
        set "PYTHON=%CD%\.venv\Scripts\python.exe"
    ) else (
        set "PYTHON=python"
    )
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verify.ps1"
exit /b %ERRORLEVEL%
