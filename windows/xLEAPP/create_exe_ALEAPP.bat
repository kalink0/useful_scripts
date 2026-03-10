@echo off
setlocal EnableDelayedExpansion

:: ------------------------------------------------------------------------------
:: AUTHOR:         kalink0
:: MAIL:           kalinko@be-binary.de
:: CREATION DATE:  2026-03-10
::
:: LICENSE:        CC0-1.0
::
:: SOURCE:         https://github.com/kalink0/useful_scripts
::
:: TITLE:          create_exe_ALEAPP.bat
::
:: DESCRIPTION:    Build Windows executable of ALEAPP (CLI and GUI) - pyinstaller
::                 Target folder: ALEAPP\dist\
::
::
:: KNOWN RESTRICTIONS:
::                 ALEAPP folder and venv must be present on system
::                 (e.g. from start_update_ALEAPP.bat)
::
:: USAGE EXAMPLE:  ./create_exe_ALEAPP.bat
::
:: -------------------------------------------------------------------------------

set "ALEAPP_DIR=%~dp0ALEAPP"
set "VENV_DIR=%ALEAPP_DIR%\venv"
set "DIST_DIR=%ALEAPP_DIR%\dist"

title ALEAPP Build Executable

echo.
echo  ============================================================
echo   ALEAPP - Build Executable via PyInstaller
echo  ============================================================
echo.

:: ------------------------------------------------------------
:: Pre-flight checks
:: ------------------------------------------------------------
if not exist "%ALEAPP_DIR%\aleappGUI.py" (
    echo  [ERROR] ALEAPP folder not found or incomplete: %ALEAPP_DIR%
    echo          Please run start_update_ALEAPP.bat first to set up ALEAPP.
    echo.
    pause
    exit /b 1
)

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo  [ERROR] Virtual environment not found: %VENV_DIR%
    echo          Please run start_update_ALEAPP.bat first to set up the venv.
    echo.
    pause
    exit /b 1
)

:: Activate venv
call "%VENV_DIR%\Scripts\activate.bat"

:: Check / install PyInstaller inside venv
echo [1/3] Checking for PyInstaller...
"%VENV_DIR%\Scripts\pyinstaller.exe" --version >nul 2>&1
if errorlevel 1 (
    echo        PyInstaller not found. Installing into venv...
    pip install pyinstaller
    echo        Verifying PyInstaller is available in venv...
    if errorlevel 1 (
        echo.
        echo  [ERROR] Failed to install PyInstaller.
        echo          Check your internet connection and try again.
        echo.
        pause
        exit /b 1
    )
    echo        PyInstaller installed. OK
) else (
    for /f "tokens=*" %%v in ('"%VENV_DIR%\Scripts\pyinstaller.exe" --version 2^>^&1') do set PIVER=%%v
    echo        PyInstaller !PIVER! found. OK
)
echo.

:: ------------------------------------------------------------
:: Choose what to build
:: ------------------------------------------------------------
echo [2/3] What do you want to build?
echo.
echo   [1] aleappGUI.exe  (GUI - recommended for end users)
echo   [2] aleapp.exe     (CLI)
echo   [3] Both
echo   [4] Cancel
echo.
set /p BUILD_CHOICE=" Enter choice (1/2/3/4): "

if "%BUILD_CHOICE%"=="1" goto :build_gui
if "%BUILD_CHOICE%"=="2" goto :build_cli
if "%BUILD_CHOICE%"=="3" goto :build_both
if "%BUILD_CHOICE%"=="4" goto :done
echo  Invalid choice. Exiting.
goto :done

:: ------------------------------------------------------------
:: Build targets
:: ------------------------------------------------------------
:build_both
call :do_build_gui
call :do_build_cli
goto :build_done

:build_gui
call :do_build_gui
goto :build_done

:build_cli
call :do_build_cli
goto :build_done

:: ------------------------------------------------------------
:: Subroutine: build GUI exe
:: ------------------------------------------------------------
:do_build_gui
echo.
echo [3/3] Building aleappGUI.exe...
cd /d "%ALEAPP_DIR%"
if not exist "Scripts\pyinstaller\aleappGUI.spec" (
    echo  [ERROR] aleappGUI.spec not found in %ALEAPP_DIR%
    echo          Cannot build without the spec file.
    goto :eof
)
"%VENV_DIR%\Scripts\pyinstaller.exe" Scripts\pyinstaller\aleappGUI.spec
if errorlevel 1 (
    echo.
    echo  [ERROR] Build failed for aleappGUI.exe. See output above.
) else (
    echo.
    echo  [OK] aleappGUI.exe built successfully.
    echo       Location: %DIST_DIR%\aleappGUI.exe
)
goto :eof

:: ------------------------------------------------------------
:: Subroutine: build CLI exe
:: ------------------------------------------------------------
:do_build_cli
echo.
echo [3/3] Building aleapp.exe...
cd /d "%ALEAPP_DIR%"
if not exist "Scripts\pyinstaller\aleapp.spec" (
    echo  [ERROR] aleapp.spec not found in %ALEAPP_DIR%
    echo          Cannot build without the spec file.
    goto :eof
)
"%VENV_DIR%\Scripts\pyinstaller.exe" Scripts\pyinstaller\aleapp.spec
if errorlevel 1 (
    echo.
    echo  [ERROR] Build failed for aleapp.exe. See output above.
) else (
    echo.
    echo  [OK] aleapp.exe built successfully.
    echo       Location: %DIST_DIR%\aleapp.exe
)
goto :eof

:: ------------------------------------------------------------
:: Post-build summary
:: ------------------------------------------------------------
:build_done
echo.
echo  ============================================================
echo   Build Summary
echo  ============================================================
echo.
if exist "%DIST_DIR%\aleappGUI.exe" (
    for %%f in ("%DIST_DIR%\aleappGUI.exe") do (
        echo   aleappGUI.exe  - %%~zf bytes
    )
) else (
    echo   aleappGUI.exe  - not built
)
if exist "%DIST_DIR%\aleapp.exe" (
    for %%f in ("%DIST_DIR%\aleapp.exe") do (
        echo   aleapp.exe     - %%~zf bytes
    )
) else (
    echo   aleapp.exe     - not built
)
echo.
echo   Output folder: %DIST_DIR%
echo.

:done
echo  Done. Press any key to close.
pause >nul
endlocal
