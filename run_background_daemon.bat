@echo off
setlocal enabledelayedexpansion
title Tech Conference Notifier - Autonomous Background Daemon

cd /d "%~dp0"

:: -------------------------------------------------------------
:: Locate Python Executable
:: -------------------------------------------------------------
set "PY_CMD="
where py >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=py -3"
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set "PY_CMD=python"
    ) else (
        if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
            set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
        ) else (
            echo [ERROR] Python 3.10+ was not found on your system.
            echo Please install Python from https://www.python.org/ or add it to PATH.
            pause
            exit /b 1
        )
    )
)

echo ====================================================================
echo   TECH CONFERENCES AND CONVENTIONS NOTIFIER - AUTONOMOUS DAEMON
echo ====================================================================
echo   Starting autonomous background scheduler...
echo   Press Ctrl+C to stop the daemon.
echo.

%PY_CMD% run_notifier.py daemon

if %errorlevel% neq 0 (
    echo [ERROR] Daemon stopped with error code %errorlevel%.
    pause
)
