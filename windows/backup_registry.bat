@echo off


:: ------------------------------------------------------------------------------
:: AUTHOR:         kalink0
:: MAIL:           kalinko@be-binary.de
:: CREATION DATE:  2018/07/14
::
:: LICENSE:        CC0-1.0
::
:: SOURCE:         https://github.com/kalink0/useful_scripts
::
:: TITLE:          backup_registry.bat
::
:: DESCRIPTION:    Script to backup the MS registry hives from a running system.
::                 Resulting files will be stored in the directory from where you called the script
::
::
:: KNOWN RESTRICTIONS:
::                 The script may be run with admin privileges
::
:: USAGE EXAMPLE:  ./backup_registry.bat
::
:: -------------------------------------------------------------------------------

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
