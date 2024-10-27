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
# DESCRIPTION:    This script is more like a collection of commands. It can be run on a live system but would use the executables on the machine, so be careful when using.
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
echo "====== LAST BOOTS AND LOGINS ====="
last
echo "====== KERNEL VERSION AND DISTRIBUTION INFO ====="
uname -a
cat /etc/issue
echo "====== ENV VARIABLES ====="
env
echo "====== HOSTNAME ====="
hostname
echo "====== NETWORK INFORMATION / INTERFACE ====="
# TODO compatiblity with older version -> e.g. ifconfig
ip a
echo "====== NETWORK INFORMATION / ROUTING ====="
ip r
echo "===== NETWORK INFORMATION / ARP ====="
# formerly "arp -a" 
# TODO compatiblity with older version 
ip -s n
echo "===== NETWORK INFORMATION / DNS CACHE ====="
journalctl -u systemd-resolved      
journalctl -u dnsmasq   
echo "===== NETWORK INFORMATION / ACTIVE SOCKETS ====="
ss -a
echo "===== NETWORK INFORMATION / OPEN PORTS ====="
ss -an
echo "===== CURRENT RUNNING PROCESSES ====="
ps -aux
echo "===== MOUNTED DEVICES / MOUNT POINTS ====="
mount
echo "===== OPEN FILES ====="
lsof
