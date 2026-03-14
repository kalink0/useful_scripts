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
:: TITLE:          start_update_iLEAPP.bat
::
:: DESCRIPTION:    Setup, update and launch iLEAPP (CLI and GUI)
::
::
:: KNOWN RESTRICTIONS:
::                 Python neeeds to be installed and in PATH.
::		   Git needs to be installed and in PATH 
::                 Internet required for first setup and updates.
::		   iLEAPP will be stored in same directory, subfolder iLEAPP
::
:: USAGE EXAMPLE:  ./start_update_ALEAPP.bat
::
:: -------------------------------------------------------------------------------

set "iLEAPP_DIR=%~dp0iLEAPP"
set "VENV_DIR=%iLEAPP_DIR%\venv"
set "REPO_URL=https://github.com/abrignoni/iLEAPP.git"
set "OFFLINE=0"

title iLEAPP Setup and Launcher

echo.
echo  ============================================================
echo   iLEAPP Setup and Launcher
echo  ============================================================
echo.

:: ------------------------------------------------------------
:: 1. Check for Python  (always required, no internet needed)
:: ------------------------------------------------------------
echo [1/4] Checking for Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Python is not installed or not in PATH.
    echo  Please install Python 3.x from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo        !PYVER! found. OK
echo.

:: ------------------------------------------------------------
:: 2. Clone or Update iLEAPP  (internet-gated)
:: ------------------------------------------------------------
echo [2/4] iLEAPP source code...

if exist "%iLEAPP_DIR%\.git" goto :repo_exists
if exist "%iLEAPP_DIR%\iLEAPPGUI.py" goto :repo_manual
goto :repo_clone

:repo_exists
:: --- Git repo already present ---
cd /d "%iLEAPP_DIR%"
for /f "tokens=*" %%b in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set GIT_BRANCH=%%b
for /f "tokens=*" %%h in ('git log -1 --format^="%%h  %%ci  %%s" 2^>nul') do set GIT_LAST=%%h
echo        Local repository found.
echo        Branch : !GIT_BRANCH!
echo        Commit : !GIT_LAST!
echo.
set /p DO_UPDATE=" Do you want to pull the latest changes from GitHub? (Y/N): "
if /i "!DO_UPDATE!"=="Y" goto :do_pull
echo        Update skipped. Using existing local version.
set "OFFLINE=1"
goto :repo_done

:do_pull
echo.
echo        Pulling latest changes...
git pull
if errorlevel 1 (
    echo  [WARNING] git pull encountered an issue. Continuing with existing files.
) else (
    echo        Repository updated. OK
)
goto :repo_done

:repo_manual
:: --- Folder exists but not a git repo (e.g. manual copy) ---
echo        iLEAPP folder found (not a git repository). Skipping update check.
set "OFFLINE=1"
goto :repo_done

:repo_clone
:: --- Nothing there yet - must clone ---
echo        No local copy found. Cloning from GitHub...
echo.
git --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Git is not installed or not in PATH.
    echo  Please install Git from https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)
git clone "%REPO_URL%" "%iLEAPP_DIR%"
if errorlevel 1 (
    echo.
    echo  [ERROR] Failed to clone the iLEAPP repository.
    echo  Check your internet connection and try again.
    echo.
    pause
    exit /b 1
)
echo        Clone successful. OK

:repo_done
echo.

:: ------------------------------------------------------------
:: 3. Create virtual environment  (no internet needed)
:: ------------------------------------------------------------
echo [3/4] Setting up Python virtual environment...
cd /d "%iLEAPP_DIR%"

if exist "%VENV_DIR%\Scripts\activate.bat" (
    echo        Virtual environment already exists. OK
) else (
    echo        Creating new virtual environment at: %VENV_DIR%
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo.
        echo  [ERROR] Failed to create virtual environment.
        echo  Ensure the 'venv' module is available for your Python installation.
        echo.
        pause
        exit /b 1
    )
    echo        Virtual environment created. OK
)
echo.

:: ------------------------------------------------------------
:: 4. Install / verify requirements
::    Skipped when offline=1 AND packages are already present.
::    pip upgrade and install only run when user chose to update.
:: ------------------------------------------------------------
echo [4/4] Checking requirements...
call "%VENV_DIR%\Scripts\activate.bat"

if "%OFFLINE%"=="1" (
    for /f %%c in ('pip list 2^>nul ^| find /c /v ""') do set PKG_COUNT=%%c
    if !PKG_COUNT! GTR 2 (
        echo        Offline mode: venv has !PKG_COUNT! packages already. Skipping install.
        echo        To update packages, re-run with internet and choose Y to update.
    ) else (
        echo  [WARNING] Offline mode but venv appears empty ^(!PKG_COUNT! packages^).
        echo            Requirements cannot be installed without internet access.
        echo            Launch may fail if packages are missing.
    )
) else (
    if exist "%iLEAPP_DIR%\requirements.txt" (
        echo        Upgrading pip...
        python -m pip install --upgrade pip --quiet
        echo        Installing / updating packages from requirements.txt...
        pip install -r "%iLEAPP_DIR%\requirements.txt"
        if errorlevel 1 (
            echo.
            echo  [ERROR] Failed to install one or more requirements.
            echo  Check the output above for details.
            echo.
            pause
            exit /b 1
        )
        echo        All requirements satisfied. OK
    ) else (
        echo  [WARNING] requirements.txt not found. Skipping package installation.
    )
)
echo.

:: ------------------------------------------------------------
:: Launch Menu
:: ------------------------------------------------------------
echo  ============================================================
echo   iLEAPP is ready!
echo  ============================================================
echo.
echo   What would you like to do?
echo.
echo   [1] Launch iLEAPP GUI  (iLEAPPGUI.py)
echo   [2] Launch iLEAPP CLI  (iLEAPP.py)
echo   [3] Exit
echo.
set /p CHOICE=" Enter choice (1/2/3): "

if "%CHOICE%"=="1" goto :launch_gui
if "%CHOICE%"=="2" goto :launch_cli
if "%CHOICE%"=="3" goto :done

echo  Invalid choice. Exiting.
goto :done

:launch_gui
echo.
echo  Launching iLEAPP GUI...
echo.
if exist "%iLEAPP_DIR%\iLEAPPGUI.py" (
    python "%iLEAPP_DIR%\iLEAPPGUI.py"
) else (
    echo  [ERROR] iLEAPPGUI.py not found in %iLEAPP_DIR%
    echo  The repository structure may have changed.
)
goto :done

:launch_cli
echo.
echo  Launching iLEAPP CLI...
echo.
if exist "%iLEAPP_DIR%\iLEAPP.py" (
    python "%iLEAPP_DIR%\iLEAPP.py" -h
    echo.
    echo  Tip: Run iLEAPP.py directly with your desired arguments.
    echo  Example: python iLEAPP.py -t android -i ^<input_path^> -o ^<output_path^>
) else (
    echo  [ERROR] iLEAPP.py not found in %iLEAPP_DIR%
    echo  The repository structure may have changed.
)
goto :done

:done
echo.
echo  Done. Press any key to close.
pause >nul
endlocal
