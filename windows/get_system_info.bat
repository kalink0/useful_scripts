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
:: TITLE:          get_system_info.bat
::
:: DESCRIPTION:    Script to get general information of a running MS Windows system.
::
::
:: KNOWN RESTRICTIONS:
::                 The script should be run with admin privileges
::
:: USAGE EXAMPLE:  ./get_system_info.bat > [output_filename]
::
:: -------------------------------------------------------------------------------

echo ====== DATE AND TIME =====
echo %date% %time%
echo ====== CURRENT USER ======
whoami
echo ====== CURRENT LOGGED IN USERS =====
qwinsta
echo ====== EXISTING USER ACCOUNTS =====
net user
echo ====== WINDOWS VERSION =====
ver
echo ====== ENV VARIABLES =====
cmd /c set
echo ====== HOSTNAME =====
hostname
echo ====== NETWORK INFORMATION / INTERFACE =====
ipconfig -all
echo ====== NETWORK INFORMATION / ROUTING =====
route PRINT
echo ===== NETWORK INFORMATION / ARP =====
arp -a
echo ===== NETWORK INFORMATION / DNS CACHE =====
ipconfig /displaydns
echo ===== NETWORK INFORMATION / ACTIVE SOCKETS =====
netstat -a
echo ===== NETWORK INFORMATION / OPEN PORTS =====
netstat -an
echo ===== CURRENT RUNNING PROCESSES =====
tasklist
echo ===== SYSTEMINFO OUTPUT =====
systeminfo
echo ===== OPEN FILES =====
net file
