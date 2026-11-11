@echo off
setlocal enabledelayedexpansion
title Tech Conference Notifier - Mobile PWA and REST API Server

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

:: -------------------------------------------------------------
:: Detect LAN IP for Mobile Device Access
:: -------------------------------------------------------------
set "LAN_IP="
for /f "delims=" %%I in ('%PY_CMD% -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()" 2^>nul') do (
    set "LAN_IP=%%I"
)
if "%LAN_IP%"=="" set "LAN_IP=127.0.0.1"

:: -------------------------------------------------------------
:: Display Connection Banner
:: -------------------------------------------------------------
cls
echo ====================================================================
echo   TECH CONFERENCES AND CONVENTIONS NOTIFIER - MOBILE APP AND API
echo ====================================================================
echo.
echo   Local Web Access    : http://localhost:5000
echo   Mobile Device Access: http://!LAN_IP!:5000
echo.
echo   Mobile Setup Instructions:
echo     1. Connect your phone or tablet to the same Wi-Fi network.
echo     2. Open your mobile browser (Safari on iOS / Chrome on Android).
echo     3. Navigate to: http://!LAN_IP!:5000
echo     4. Tap "Share" (iOS) or "..." (Android) -^> "Add to Home Screen"
echo        to install as a native offline-ready Progressive Web App!
echo.
echo ====================================================================
echo   Starting Mobile Flask Backend and PWA Server on 0.0.0.0:5000...
echo   Press Ctrl+C to stop the server at any time.
echo ====================================================================
echo.

:: Automatically open default browser after a brief delay
start "" http://localhost:5000

:: Run API server
%PY_CMD% run_notifier.py serve --host 0.0.0.0 --port 5000

if %errorlevel% neq 0 (
    echo [ERROR] Server exited with error code %errorlevel%.
    pause
)
