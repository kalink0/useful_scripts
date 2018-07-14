@echo off


REM ------------------------------------------------------------------------------
REM AUTHOR:         kalink0
REM MAIL:           kalinko@be-binary.de
REM CREATION DATE:  2018/07/14
REM
REM LICENSE:        CC0-1.0
REM
REM SOURCE:         https://github.com/kalink0/useful_scripts
REM
REM TITLE:          backup_registry.bat
REM
REM DESCRIPTION:    Script to backup the MS registry hives from a running system.
REM                 Resulting files will be stored in the directory from where you called the script
REM
REM
REM KNOWN RESTRICTIONS:
REM                 The script may be run with admin privileges
REM
REM USAGE EXAMPLE:  ./backup_registry.bat
REM
REM -------------------------------------------------------------------------------

echo Export HKLM
reg export HKLM hklm.reg > nul
echo Export HKCU
reg export HKCU hkcu.reg > nul
echo Export HKCR
reg export HKCR hkcr.reg > nul
echo Export HKU
reg export HKU  hku.reg > nul
echo Export HKCC
reg export HKCC hkcc.reg > nul
