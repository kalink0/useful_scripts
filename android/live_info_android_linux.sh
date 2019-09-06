#!/bin/bash
# ------------------------------------------------------------------------------
# AUTHOR:         kalink0
# MAIL:           kalinko@be-binary.de
# CREATION DATE:  2019/09/06
#
# LICENSE:        CC0-1.0
#
# SOURCE:         https://github.com/kalink0/useful_scripts/android
#
# TITLE:          live_info_android_linux.sh
#
# DESCRIPTION:    Script to get live system information from Android system
#				  via ADB
#
#
# KNOWN RESTRICTIONS:
#                 Only usable with ADB connection to Android phone and on a 
#                 Nix system
#				  When starting the script the adb connection must already been
#				  trusted.
#
# USAGE EXAMPLE:  Execute Script on your system with attached Android phone.
#				  
#
#-------------------------------------------------------------------------------


# Get current system date and time
DATE_NOW = $(date +"%Y-%m-%d %H:%M:%S %z")


