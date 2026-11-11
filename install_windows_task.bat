@echo off
setlocal enabledelayedexpansion
title Tech Conference Notifier - Install Windows Scheduled Task

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
echo   TECH CONFERENCES AND CONVENTIONS NOTIFIER - TASK INSTALLER
echo ====================================================================
echo.
echo   Registering background task with Windows Task Scheduler...
echo   (Configured to run silently under pythonw.exe with zero console popups)
echo.

%PY_CMD% run_notifier.py install-task

echo.
pause
