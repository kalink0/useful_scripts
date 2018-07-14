# ------------------------------------------------------------------------------
# AUTHOR:         kalink0
# MAIL:           kalinko@be-binary.de
# CREATION DATE:  2018/07/14
#
# LICENSE:        CC0-1.0
#
# SOURCE:         https://github.com/kalink0/useful_scripts
#
# TITLE:          get_BitLocker_Recovery_Key.ps1
#
# DESCRIPTION:    Script to read out the Recovery Key of BitLocker Volumes from a running system.
#
#
# KNOWN RESTRICTIONS:
#                 The script may be run with admin privileges
#
# USAGE EXAMPLE:  ./get_BitLocker_Recovery_Key.ps1 > [output_filename]
#
#-------------------------------------------------------------------------------


# First get all available volume in the system that could use Bitlocker
Get-BitLockerVolume

# Now print all Recovery key and basic information for the volumes that actually use BitLocker
(Get-BitLockerVolume).KeyProtector
