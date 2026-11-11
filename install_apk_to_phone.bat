@echo off
setlocal
echo ======================================================================
echo   TECH CONFERENCE NOTIFIER - ANDROID APK INSTALLER
echo ======================================================================
echo.

set APK_FILE=TechConfNotifier.apk
if not exist "%APK_FILE%" (
    set APK_FILE=android_app\app\build\outputs\apk\debug\app-debug.apk
)

if not exist "%APK_FILE%" (
    echo [ERROR] APK file not found. Please build the APK first.
    pause
    exit /b 1
)

set ADB_PATH=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe
if not exist "%ADB_PATH%" (
    set ADB_PATH=adb
)

echo [1/3] Checking for connected Android devices via ADB...
"%ADB_PATH%" devices
echo.

echo [2/3] Installing %APK_FILE% to your phone...
"%ADB_PATH%" install -r "%APK_FILE%"
if %errorlevel% neq 0 (
    echo.
    echo [NOTICE] If installation failed, make sure:
    echo   1. Your Android phone is connected via USB cable (or wireless ADB).
    echo   2. 'Developer Options' and 'USB Debugging' are enabled on your phone.
    echo   3. Alternatively, you can copy 'TechConfNotifier.apk' directly to
    echo      your phone (via Google Drive, USB, or Bluetooth) and tap it to install!
    echo.
    pause
    exit /b 1
)

echo.
echo [3/3] Launching TechConf Notifier on your phone...
"%ADB_PATH%" shell am start -n com.techconf.notifier/.MainActivity
echo.
echo ======================================================================
echo   INSTALLATION COMPLETED SUCCESSFULLY!
echo   The app is now running independently on your Android phone.
echo ======================================================================
pause
