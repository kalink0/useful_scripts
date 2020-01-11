#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# AUTHOR:         kalink0
# MAIL:           kalinko@be-binary.de
# CREATION DATE:  2020/01/09
#
# LICENSE:        CC0-1.0
#
# SOURCE:         https://github.com/kalink0/useful_scripts/windows
#
# TITLE:         find_similar_images.py
#
# DESCRIPTION:   TBD
#
# KNOWN RESTRICTIONS:
#               TBD
#
# USAGE EXAMPLE:
#            TBD
#
# -------------------------------------------------------------------------------

import argparse
import os
import dhash
import PIL
from wand.image import Image

def calculate_dhashes (files):

    dhashes = []
    for i in files:
        image = PIL.Image.open(i)
        row, col = dhash.dhash_row_col(image)
        print (i)
        print(dhash.format_hex(row, col))

def ccalculate_dhashes_2 (files):
    for i in files:
        with Image(filename=i) as image:
            row, col = dhash.dhash_row_col(image)
            print (i)
            print(dhash.format_hex(row, col))

def create_file_list (data_set):
    file_list = []
    for root, dirs, files in os.walk(data_set):
        for file in files:
            file_list.append(os.path.join(root, file))
    return file_list

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
        description="Script to calculate dhashes of images and find images with identical dhash"
    )

    ap.add_argument("image")
    ap.add_argument("data_set")
    
    #args = ap.parse_args()
    #file_list = create_file_list ("/home/kalinko/Nextcloud/Work/Tests/DHash/testset/")
    file_list = create_file_list ("D:\\Nextcloud\\Work\\Tests\\DHash\\testset\\")
    calculate_dhashes(file_list)
    ccalculate_dhashes_2(file_list)


if __name__ == "__main__":
    main()

