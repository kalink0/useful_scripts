#!/bin/bash
# ------------------------------------------------------------------------------
# AUTHOR:         kalink0
# MAIL:           kalinko@be-binary.de
# CREATION DATE:  2018/07/14
#
# LICENSE:        CC0-1.0
#
# SOURCE:         https://github.com/kalink0/useful_scripts
#
# TITLE:          get_system_info.sh
#
# DESCRIPTION:    Script get general information of a running linux system. 
#
#
# KNOWN RESTRICTIONS:
#                 The script should be run as super user
#
# USAGE EXAMPLE:  ./get_system_info.sh > [output_filename]
#
#-------------------------------------------------------------------------------

echo "===== CURRENT DATE AND TIME ====="
date
echo "====== CURRENT USER  ======"
whoami
echo "====== CURRENT LOGGED IN USERS ====="
w
echo "====== EXISTING LOCAL USER ACCOUNTS ====="
cut -d: -f1 /etc/passwd
echo "====== KERNEL VERSION AND DISTRIBUTION INFO ====="
uname -a
cat /etc/issue
echo "====== ENV VARIABLES ====="
env
echo "====== HOSTNAME ====="
hostname
echo "====== NETWORK INFORMATION / INTERFACE ====="
# TODO compatiblity with older version -> e.g. ifconfig
ip addr
echo "====== NETWORK INFORMATION / ROUTING ====="
route
echo "===== NETWORK INFORMATION / ARP ====="
arp -a
echo "===== NETWORK INFORMATION / DNS CACHE ====="
# TODO Control if nscd is running and installed, only than execute this command
nscd -g
echo "===== NETWORK INFORMATION / ACTIVE SOCKETS ====="
netstat -a
echo "===== NETWORK INFORMATION / OPEN PORTS ====="
netstat -an
echo "===== CURRENT RUNNING PROCESSES ====="
ps -aux
echo "===== MOUNT POINTS ====="
mount
echo "===== OPEN FILES ====="
lsof
