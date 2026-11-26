@echo off
setlocal

:: ------------------------------------------------------------------------------
:: AUTHOR:         kalink0 (Marco Neumann)
:: CREATION DATE:  2026-11-25
::
:: LICENSE:        CC0-1.0
::
:: TITLE:          build_exe.bat
::
:: DESCRIPTION:    Build Windows executables of basil.py - pyinstaller
::                   dist\basil_gui.exe  (GUI, no console window)
::                   dist\basil.exe      (CLI, starts the GUI without arguments)
::
:: KNOWN RESTRICTIONS:
::                 Python 3.8+ must be installed and on PATH (py launcher or python)
::                 Internet access needed once to install PyInstaller into the venv
::
:: USAGE EXAMPLE:  build_exe.bat
::
:: -------------------------------------------------------------------------------

cd /d "%~dp0"
set "VENV_DIR=%~dp0.venv-build"

where py >nul 2>&1 && (set "PY=py -3") || (set "PY=python")

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [1/3] Creating build venv...
    %PY% -m venv "%VENV_DIR%" || goto :error
)

echo [2/3] Installing / checking PyInstaller...
"%VENV_DIR%\Scripts\python.exe" -m pip install --quiet --upgrade pyinstaller -r requirements.txt || goto :error

echo [3/3] Building executables...
"%VENV_DIR%\Scripts\pyinstaller.exe" --noconfirm --clean --onefile --windowed --collect-all tkinterdnd2 --icon basil.ico --name basil_gui basil.py || goto :error
"%VENV_DIR%\Scripts\pyinstaller.exe" --noconfirm --onefile --console --collect-all tkinterdnd2 --icon basil.ico --name basil basil.py || goto :error

echo.
echo  [OK] Done. Executables in: %~dp0dist
dir /b dist\*.exe
echo.
pause
exit /b 0

:error
echo.
echo  [ERROR] Build failed. See output above.
pause
exit /b 1
