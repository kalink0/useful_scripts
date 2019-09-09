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
#				          via ADB
#
#
# KNOWN RESTRICTIONS:
#                 - Only usable with ADB connection to Android phone and on a
#                   Windows system
#				  - When starting the script the adb connection must already been
#				    trusted.
#				  - Logcat command needs to be run twice beacuse the option "-b all"
#				    Is not usable on older Versions of Android
#
#
# USAGE EXAMPLE:  Execute Script on your system with attached Android phone.
#                 The script will ask for a target directory and a device id.
#                 The device ID will be the prefix of the created files.
#
#-------------------------------------------------------------------------------

## Ask for dirctory name and Device name/id
read -p 'Destination directory: ' DEST_DIR
read -p 'Device ID: ' DEVICE_ID

mkdir $DEST_DIR

# Get current date and time of system and device
DATE_SYSTEM_NOW=$(date +"%Y-%m-%d %H:%M:%S %z")
DATE_DEVICE_NOW=$(adb shell "date +'%Y-%m-%d %H:%M:%S %z'")

# logcat complete
echo "1. GETTING LOGS FROM DEVICE VIA LOGCAT"
# TODO: Make logcat dependent on the Android Version or the output of it
# Because the next line doesn't run on older Androids
adb shell logcat -d -b all > $DEST_DIR/$DEVICE_ID\_logcat.log
adb shell logcat -d > $DEST_DIR/$DEVICE_ID\_logcat.log
adb shell logcat -S -b all > $DEST_DIR/$DEVICE_ID\_logcat_top.txt
# dumpsys complete
echo "2. CREATING SYSTEM DUMP"
adb shell dumpsys > $DEST_DIR/$DEVICE_ID\_dumpsys_complete
# dumpsys specific - to get more specific and faster view on some parts
adb shell dumpsys activity > $DEST_DIR/$DEVICE_ID\_dumpsys_activity
adb shell dumpsys account > $DEST_DIR/$DEVICE_ID\_dumpsys_account
adb shell dumpsys wifi > $DEST_DIR/$DEVICE_ID\_dumpsys_wifi
adb shell dumpsys dbinfo > $DEST_DIR/$DEVICE_ID\_dumpsys_dbinfo
adb shell dumpsys usagestats > $DEST_DIR/$DEVICE_ID\_dumpsys_usagestats
adb shell dumpsys procstats full-details > $DEST_DIR/$DEVICE_ID\_dumpsys_procstats

# getprop complete
echo "3. STORING DEVICE PROPERTIES"
adb shell getprop > $DEST_DIR/$DEVICE_ID\_properties

# installed packages
echo "4. GETTING INFO ABOUT INSTALLED PACKAGES"
## system enabled
echo "==== ENABLED SYSTEM PACKAGES ====" > $DEST_DIR/$DEVICE_ID\_packages.lst
adb shell pm list packages -s -e >> $DEST_DIR/$DEVICE_ID\_packages.lst
## system disabled
echo "" >> $DEST_DIR/$DEVICE_ID\_packages.lst
echo "==== DISABLED SYSTEM PACKAGES ====" >> $DEST_DIR/$DEVICE_ID\_packages.lst
adb shell pm list packages -s -d >> $DEST_DIR/$DEVICE_ID\_packages.lst
## non-system enabled
echo "" >> $DEST_DIR/$DEVICE_ID\_packages.lst
echo "==== ENABLED 3RD-PARTY PACKAGES ====" >> $DEST_DIR/$DEVICE_ID\_packages.lst
adb shell pm list packages -3 -e >> $DEST_DIR/$DEVICE_ID\_packages.lst
## non-system disabled
echo "" >> $DEST_DIR/$DEVICE_ID\_packages.lst
echo "==== DISABLED 3RD-PARTY PACKAGES ====" >> $DEST_DIR/$DEVICE_ID\_packages.lst
adb shell pm list packages -3 -d >> $DEST_DIR/$DEVICE_ID\_packages.lst

# System settings
echo "5. SAVING SYSTEM SETTINGS"
adb shell settings list global > $DEST_DIR/$DEVICE_ID\_settings_global
adb shell settings list system > $DEST_DIR/$DEVICE_ID\_settings_system
adb shell settings list secure > $DEST_DIR/$DEVICE_ID\_settings_secure

echo "6. GETTING STORAGE INFORMATION"
# Partitions (Does work on Android 7, does not work on Android 9)
adb shell cat /proc/partitions > $DEST_DIR/$DEVICE_ID\_storage
# Mounted partitions including there mountpoints and current utilization
adb shell df -h >> $DEST_DIR/$DEVICE_ID\_storage



echo "7. GETTING DEVICE INFORMATION AND CREATING DEVICE SUMMARY"
# rooted or not
if [[ $(adb shell id) == *"root"* ]] || [[ $(adb shell su -c id) == *"root"* ]];then
	ROOTED="TRUE"
else
  ROOTED="FALSE"
fi

# Current SIM Card infos (TODO: Handle more than one SIM)
# Doesn'T work really well, need better parsing because the values are not always
# at the same place
#PHONE_NUMBER=$(adb shell service call iphonesubinfo 13 | awk -F "'" '{print $2}' | sed '1 d'| tr -d '\n' | tr -d '.' | tr -d ' ')
#ICCID=$(adb shell service call iphonesubinfo 11 | awk -F "'" '{print $2}' | sed '1 d'| tr -d '\n' | tr -d '.' | tr -d ' ')

# NAME and MAC Bluetooth
MAC_BT=$(adb shell settings get secure bluetooth_address)
NAME_BT=$(adb shell settings get secure bluetooth_name)
# MAC WIFI - Works on Android Moto g6 - needs more testing
WIFI_MAC=$(adb shell getprop ro.boot.wifimacaddr)

# IMEI
IMEI1=$(adb shell service call iphonesubinfo 1 | awk -F "'" '{print $2}' | sed '1 d'| tr -d '\n' | tr -d '.' | tr -d ' ')
IMEI2=$(adb shell service call iphonesubinfo 3 | awk -F "'" '{print $2}' | sed '1 d'| tr -d '\n' | tr -d '.' | tr -d ' ')
if [ $IMEI1 == $IMEI2 ]; then
  IMEI2=""
fi

# Serial Number
# TODO: Not tested on enoguh devices. More testing necessary
SERIAL_SAM=$(adb shell getprop ril.serialnumber) # For Samsung
SERIAL_MOTO=$(adb shell getprop ro.vendor.boot.serialno) # For Motorola
if [[ -z $SERIAL_SAM ]]; then
  SERIAL=$SERIAL_MOTO
else
  SERIAL=$SERIAL_SAM
fi

# ENcrypted or not encrypted? And Type
CRYPTO_STATE=$(adb shell getprop ro.crypto.state)
CRYPTO_TYPE=$(adb shell getprop ro.crypto.type)

# Chipset/Hardware
HARDWARE=$(adb shell getprop ro.boot.hardware)
PLATFORM=$(adb shell getprop ro.board.platform)

# Model and Manfacturer
MANUFACTURER=$(adb shell getprop ro.product.manufacturer)
MODEL=$(adb shell getprop ro.product.model)
NAME=$(adb shell getprop ro.product.name)

# CSC version (Only Samsung)
CSC_CODE=$(adb shell getprop ro.csc.sales_code)
# Android Version
ANDROID_VERSION=$(adb shell getprop ro.build.version.release)
# Buildnumber
BUILDNUMBER=$(adb shell getprop ro.build.display.id)
# Patchlevel
PATCHLEVEL=$(adb shell getprop ro.build.version.security_patch)

# And now we print out a summary and additionaly write the summary into a file
SUM_FILE=$DEVICE_ID\_summary.txt

echo "============================" | tee $DEST_DIR/$SUM_FILE
echo "====== Device Summary ======" | tee -a $DEST_DIR/$SUM_FILE
echo "============================" | tee -a $DEST_DIR/$SUM_FILE

echo "" | tee -a $DEST_DIR/$SUM_FILE
echo "Time of Android:   $DATE_DEVICE_NOW" | tee -a $DEST_DIR/$SUM_FILE
echo "Time of Machine:   $DATE_SYSTEM_NOW" | tee -a $DEST_DIR/$SUM_FILE

echo "" | tee -a $DEST_DIR/$SUM_FILE
echo "Manufacturer:     $MANUFACTURER" | tee -a $DEST_DIR/$SUM_FILE
echo "Model:            $MODEL" | tee -a $DEST_DIR/$SUM_FILE
echo "Name:             $NAME" | tee -a $DEST_DIR/$SUM_FILE
echo "Rooted?:          $ROOTED" | tee -a $DEST_DIR/$SUM_FILE
echo "Encrypted?:       $CRYPTO_STATE" | tee -a $DEST_DIR/$SUM_FILE

echo "" | tee -a $DEST_DIR/$SUM_FILE
echo "=== SOFTWARE INFORMATION ===" | tee -a $DEST_DIR/$SUM_FILE
echo "Android Version:  $ANDROID_VERSION" | tee -a $DEST_DIR/$SUM_FILE
echo "Build Number:     $BUILDNUMBER" | tee -a $DEST_DIR/$SUM_FILE
echo "Patchlevel:       $PATCHLEVEL" | tee -a $DEST_DIR/$SUM_FILE
echo "CSC-Code:         $CSC_CODE" | tee -a $DEST_DIR/$SUM_FILE

echo "" | tee -a $DEST_DIR/$SUM_FILE
echo "=== HARDWARE INFORMATION ===" | tee -a $DEST_DIR/$SUM_FILE
echo "Chipset:          $HARDWARE" | tee -a $DEST_DIR/$SUM_FILE
echo "Platform:         $PLATFORM" | tee -a $DEST_DIR/$SUM_FILE
echo "IMEI 1:           $IMEI1" | tee -a $DEST_DIR/$SUM_FILE
echo "IMEI 2:           $IMEI2" | tee -a $DEST_DIR/$SUM_FILE
echo "Serial number:    $SERIAL" | tee -a $DEST_DIR/$SUM_FILE
echo "WIFI MAC:         $WIFI_MAC" | tee -a $DEST_DIR/$SUM_FILE
echo "Bluetooth MAC:    $MAC_BT" | tee -a $DEST_DIR/$SUM_FILE
echo "Bluetooth Name:   $NAME_BT" | tee -a $DEST_DIR/$SUM_FILE

#echo "" | tee -a $DEST_DIR/$SUM_FILE
#echo "=== SIM CARD INFORMATION ===" | tee -a $DEST_DIR/$SUM_FILE
#echo "Phone number:     $PHONE_NUMBER" | tee -a $DEST_DIR/$SUM_FILE
#echo "ICCID:            $ICCID" | tee -a $DEST_DIR/$SUM_FILE
