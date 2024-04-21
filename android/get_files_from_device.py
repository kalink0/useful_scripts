#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# AUTHOR:         kalink0
# MAIL:           kalinko@be-binary.de
# CREATION DATE:  2019/10/25
#
# LICENSE:        CC0-1.0
#
# SOURCE:         https://github.com/kalink0/useful_scripts/android
#
# TITLE:         get_files_from_device
#
# DESCRIPTION:   Script to get files from an Android device with su installed
#                E.g. to get the file system content of an app
#
# KNOWN RESTRICTIONS:
#               Device must be connected with adb enabled and already trusted
#               Currenty only one folder/file per run can be extracted.
#               Batch mode will be implemented next
#               There needs to be free storage on the device, /data/local/tmp is used.
#               CAUTION: Existing files will be overwritten!
#
# USAGE EXAMPLE:
#            python get_files_from_device.py /data/data/com.whatsapp my_whatsapp.tar
#
# -------------------------------------------------------------------------------

import os
import argparse

def extract_data(data, dst):
    os.system("adb shell tar -cf /data/local/tmp/output_temp.tar " + data)
    os.system("adb shell chown shell:shell /data/local/tmp/output_temp.tar")
    os.system("adb pull /data/local/tmp/output_temp.tar " + dst)
    os.system("adb shell rm -f /data/local/tmp/output_temp.tar")

def create_abs_path(path):
    """
    Method to create absolute pathes if necessary
    :param path: given path, either absolute or relative
    :return:
    """
    work_dir = os.getcwd()
    if os.path.isabs(path):
        return path
    else:
        return os.path.join(work_dir, path)

def main():
    ap = argparse.ArgumentParser(
        description="Script to get files from an Android device " +
                    "with su installed"
    )

    ap.add_argument("data_to_extract")
    ap.add_argument("destination")
    # TODO: Add batch mode to read multiple values to extract from a file

    args = ap.parse_args()

    extract_data(args.data_to_extract, create_abs_path(args.destination))

if __name__ == "__main__":
    main()
