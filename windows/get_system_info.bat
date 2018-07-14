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
REM TITLE:          get_system_info.bat
REM
REM DESCRIPTION:    Script to get general information of a running MS Windows system.
REM
REM
REM KNOWN RESTRICTIONS:
REM                 The script should be run with admin privileges
REM
REM USAGE EXAMPLE:  ./get_system_info.bat > [output_filename]
REM
REM -------------------------------------------------------------------------------

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
