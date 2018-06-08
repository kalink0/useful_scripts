#!/bin/bash


if [ $# -le 1 ]
then
  echo "Usage: " $0 " <nanddumpfile> <directory to save dbs>"
else
  dumpfileescaped=`echo "$1" | sed -e "s/\//\\\\\\\\\//g"`
  dirnameescaped=`echo "$2" | sed -e "s/\//\\\\\\\\\//g"`
  mkdir -p $2
  fls -o 6586368 -r $1 | grep -i "\.jpg$" | grep -v "*" | awk '{print $3 " " $4}' | sed -e "s/:/\ $dumpfileescaped\ $dirnameescaped/g" | awk '{system("icat " $2 " -o 6586368 " $1 " > " $3 "/" $4 " && echo extracting: "$4" \n")}'
fi
