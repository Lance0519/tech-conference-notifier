@echo off
setlocal enabledelayedexpansion
title Tech Conference Notifier - Immediate CLI Sync

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
echo   TECH CONFERENCES AND CONVENTIONS NOTIFIER - CLI SYNC RUNNER
echo ====================================================================
echo   Starting discovery across Regional PH, Confs.tech, CCF Deadlines,
echo   and Custom JSON sources...
echo.

%PY_CMD% run_notifier.py sync

echo.
echo ====================================================================
echo   Sync process finished. Check upcoming_conferences.html/.md for
echo   the generated visual digest.
echo ====================================================================
echo.
if /i not "%~1"=="--silent" if /i not "%~1"=="--no-pause" (
    pause
)
