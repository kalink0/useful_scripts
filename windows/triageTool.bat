@echo off
setlocal enabledelayedexpansion


:: ------------------------------------------------------------------------------
:: AUTHOR:         kalink0
:: MAIL:           kalinko@be-binary.de
:: CREATION DATE:  2018/07/14
::
:: LICENSE:        CC0-1.0
::
:: SOURCE:         https://github.com/kalink0/useful_scripts
::
:: TITLE:          triageTool.bat
::
:: DESCRIPTION:    Triage Script to get relevant infos of eunning system and check for encryption and passwords.
::				   Displayed language is German.	
::
::
:: KNOWN RESTRICTIONS:
::                 The script uses executables from NirSoft to get and store system information.
::
:: USAGE EXAMPLE:  ./triageTool.bat
::
:: -------------------------------------------------------------------------------


echo =======================================================================
echo Skript zum Auslesen von Systeminformationen und erkennen von Verschluesselungsprogrammen auf Computern mit WIndows-Betriebssystemen
echo =======================================================================


call :check_permission
if errorlevel 1 (
	echo ACHTUNG Das Skript wurde ohne Administratorrechte gestartet! & echo.
	echo ">>> Ohne Administratorrechte koennen nicht alle Daten ausgelesen werden. Wirklich ohne Administratorrechte fortsetzen?"
	set mode=noadmin
	set /P continue=[j/N]
	if "!continue!"=="j"  (
		goto :continue_script
	) 
	if "!continue!"=="J" (
		goto :continue_script
	)
	goto :end_of_script
)


:continue_script

	
:: Get to the directory of the script, necessary if started as administrator
@cd /d "%~dp0"

:: get current time of the system to use in file name
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /format:list') do set datetime=%%I
set datetime=%datetime:~0,8%-%datetime:~8,6%


:: create target folders
IF not exist .\%COMPUTERNAME%_%datetime% (mkdir .\%COMPUTERNAME%_%datetime%)
IF not exist .\%COMPUTERNAME%_%datetime%\reports (mkdir .\%COMPUTERNAME%_%datetime%\reports)
IF not exist .\%COMPUTERNAME%_%datetime%\bitlocker (mkdir .\%COMPUTERNAME%_%datetime%\bitlocker)


:: Create report of running PC

echo =======================================================================

echo. & echo Erstelle Report, bitte warten! & echo.

.\WinAudit\WinAudit.exe /r=gsoPxuTUeERNtnzDaIbMpmidcSArCOHG /T=datetime /f=.\%COMPUTERNAME%_%datetime%\reports\%COMPUTERNAME%.html

echo Report erstellt! & echo.


pause

:: Check for running BitLocker encryption on PC and get the Recovery Key if BitLocker is running
echo =======================================================================
echo. & echo Pruefe auf BitLocker Verschluesselung & echo.

if "!mode!"=="noadmin" (
	echo Keine Adminrechte, keine Auswertung fuer Bitlocker moeglich. & echo.
	goto :skipped_bitlocker
)

powershell -command "Get-BitLockerVolume" | findstr /I "FullyEncrypted"
if errorlevel 1 (
	echo BitLocker auf keinem Laufwerk aktiviert.
) else (
	echo. & echo Auf obigen Laufwerken ist BitLocker aktiviert. Hole nun Recovery Key. & echo.
	powershell -command "Get-BitLockerVolume "; "(Get-BitLockerVolume).KeyProtector"  > .\%COMPUTERNAME%_%datetime%\bitlocker\%COMPUTERNAME%_bitlocker_%datetime%.txt
)

:skipped_bitlocker

:: Check for running encryption programs e.g. VeraCrypt and show message if something is running
echo =======================================================================

echo. & echo Pruefe auf eventuell laufende Verschluesselungsprogramme & echo.

tasklist | findstr /I "crypt" 
if errorlevel 1 (
	echo. & echo Keine bekannten Programme gefunden!  & echo. 
) else (
	echo. & echo Obige laufende Programe gefunden, bitte pruefen.  & echo. 
	pause
)

:: Check for running password containers e.g. KeePass and show message if something is running
echo =======================================================================
echo. & echo Pruefe auf eventuell geoeffnete Passwordcontainer (z.B. Keepass). & echo.

tasklist | findstr /I "pass vault" 
if errorlevel 1 (
	echo. & echo Keine bekannten Programme gefunden! & echo. 
) else (
	echo. & echo Obige laufende Programe gefunden, bitte pruefen. & echo. 
	pause
)

echo =======================================================================

echo Vorgang abgeschlossen!
pause

:end_of_script
:: Clean the variable
set answer=
set mode=

EXIT /B %ERRORLEVEL%



:: Funktion zum prüfen auf aktuelle Rechte
:check_permission
	net session >nul 2>&1
	if %errorlevel% == 0 (
		EXIT /B 0
	) else (
		EXIT /B 1
	)	






:: TODO: Get Passwords out of Browser and network shares
:: TODO: Backup the Registry, make memory dump...