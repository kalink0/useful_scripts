#!/bin/bash
# ------------------------------------------------------------------------------
# AUTHOR:         kalink0
# MAIL:           kalinko@be-binary.de
# CREATION DATE:  2018/06/30
#
# SOURCE:         https://github.com/kalink0/useful_scripts
#
# TITLE:          extract_data_tsk.sh
#
# DESCRIPTION:    Script to export files via the tool icat from The Sleuth Kit
#                 out of images. An offset and a Regex for file extensions must
#                 be given.
#
#
# KNOWN RESTRICTIONS:
#                 Duplicate file names will lead to overwrite the formlery
#                 exported file with the same name.
#
# USAGE EXAMPLE:  ./extract_data_tsk.sh test.e01 output_dir \.jpg$ 2048         
#
#-------------------------------------------------------------------------------

if [ $# -le 1 ]
then
  echo "Usage: " $0 " <image file> <directory to save exported files> <regex to identify files> <offset of disk partition>"
else
  # store the variables from the cli
  image_name=$1
  dir_name=$2
  regex=$3
  offset=$4
  temp_file="extract_data_tsk_temp"

  mkdir -p $dir_name

  # find all wanted files and store the list in a temporary file
  fls -o $offset -r $image_name | egrep -i "$regex" | grep -v "*" | sed -e "s|+\s||g" | awk '{print $2 " " $3}' | sed -e "s|:|\ $image_name\ $dir_name\ $offset|g" > /tmp/$temp_file

  # export the identified files
  cat /tmp/$temp_file | awk '{system("icat -o " $4 " " $2 " " $1 " > " $3 "/" $5 " && echo extracting: "$5" \n")}'

  # remove created temporary file
  rm /tmp/$temp_file

fi
