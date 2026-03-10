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
:: TITLE:          create_exe_iLEAPP.bat
::
:: DESCRIPTION:    Build Windows executable of iLEAPP (CLI and GUI) - pyinstaller
::                 Target folder: iLEAPP\dist\
::
::
:: KNOWN RESTRICTIONS:
::                 iLEAPP folder and venv must be present on system
::                 (e.g. from start_update_iLEAPP.bat)
::
:: USAGE EXAMPLE:  ./create_exe_iLEAPP.bat
::
:: -------------------------------------------------------------------------------

set "iLEAPP_DIR=%~dp0iLEAPP"
set "VENV_DIR=%iLEAPP_DIR%\venv"
set "DIST_DIR=%iLEAPP_DIR%\dist"

title iLEAPP Build Executable

echo.
echo  ============================================================
echo   iLEAPP - Build Executable via PyInstaller
echo  ============================================================
echo.

:: ------------------------------------------------------------
:: Pre-flight checks
:: ------------------------------------------------------------
if not exist "%iLEAPP_DIR%\iLEAPPGUI.py" (
    echo  [ERROR] iLEAPP folder not found or incomplete: %iLEAPP_DIR%
    echo          Please run start_update_iLEAPP.bat first to set up iLEAPP.
    echo.
    pause
    exit /b 1
)

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo  [ERROR] Virtual environment not found: %VENV_DIR%
    echo          Please run start_update_iLEAPP.bat first to set up the venv.
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
echo   [1] iLEAPPGUI.exe  (GUI - recommended for end users)
echo   [2] iLEAPP.exe     (CLI)
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
echo [3/3] Building iLEAPPGUI.exe...
cd /d "%iLEAPP_DIR%"
if not exist "Scripts\pyinstaller\iLEAPPGUI.spec" (
    echo  [ERROR] iLEAPPGUI.spec not found in %iLEAPP_DIR%
    echo          Cannot build without the spec file.
    goto :eof
)
"%VENV_DIR%\Scripts\pyinstaller.exe" Scripts\pyinstaller\iLEAPPGUI.spec
if errorlevel 1 (
    echo.
    echo  [ERROR] Build failed for iLEAPPGUI.exe. See output above.
) else (
    echo.
    echo  [OK] iLEAPPGUI.exe built successfully.
    echo       Location: %DIST_DIR%\iLEAPPGUI.exe
)
goto :eof

:: ------------------------------------------------------------
:: Subroutine: build CLI exe
:: ------------------------------------------------------------
:do_build_cli
echo.
echo [3/3] Building iLEAPP.exe...
cd /d "%iLEAPP_DIR%"
if not exist "Scripts\pyinstaller\iLEAPP.spec" (
    echo  [ERROR] iLEAPP.spec not found in %iLEAPP_DIR%
    echo          Cannot build without the spec file.
    goto :eof
)
"%VENV_DIR%\Scripts\pyinstaller.exe" Scripts\pyinstaller\iLEAPP.spec
if errorlevel 1 (
    echo.
    echo  [ERROR] Build failed for iLEAPP.exe. See output above.
) else (
    echo.
    echo  [OK] iLEAPP.exe built successfully.
    echo       Location: %DIST_DIR%\iLEAPP.exe
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
if exist "%DIST_DIR%\iLEAPPGUI.exe" (
    for %%f in ("%DIST_DIR%\iLEAPPGUI.exe") do (
        echo   iLEAPPGUI.exe  - %%~zf bytes
    )
) else (
    echo   iLEAPPGUI.exe  - not built
)
if exist "%DIST_DIR%\iLEAPP.exe" (
    for %%f in ("%DIST_DIR%\iLEAPP.exe") do (
        echo   iLEAPP.exe     - %%~zf bytes
    )
) else (
    echo   iLEAPP.exe     - not built
)
echo.
echo   Output folder: %DIST_DIR%
echo.

:done
echo  Done. Press any key to close.
pause >nul
endlocal
