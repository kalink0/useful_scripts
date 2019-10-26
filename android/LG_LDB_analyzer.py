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
# TITLE:         LG_LDB_analyzer
#
# DESCRIPTION:   TODO
#
# KNOWN RESTRICTIONS:
#
#
# USAGE EXAMPLE:  TODO
#
# -------------------------------------------------------------------------------

import argparse
import os
import sqlite3
import pathlib
import re
import datetime
import csv


select_version = "select * from t101;"
select_phone_info = "select * from t301;"
select_app_history = "select * from t305;"

# # store the data from the table into a multi-dim array
# array_cache_db = cursor.fetchall()

# # Header, first variant, 12 bytes long
# header = "\x04\x00\x00\x00I\x00\x00\x00I\x00\x00\x00"
# # Footer; 77 bytes long
# footer = "\x01\x00\x00\x00\x01\x04\x00\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x03\x00\x00\x00\x04\x00\x00\x00\x02" \
# "\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
# "\x00\x08\x00\x00\x00\x97\xf6\x9dX\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"

# # delete all entries that leads to a media_cache file. We cannot use them to trace sending/receiving.
# # remove unnecessary rows
# regex = re.compile(b"i\d{4}|\$CACHE")
# cleaned_array = [i for i in array_cache_db if not regex.search(i[2])]
# # we don't need the original one anymore, so let's delete it
# del array_cache_db[:]

# # now lets remove the header and footer in the encoded field so we can create a default string with the
# # content to get the path
# for i in cleaned_array:
# temp = (i[2][12:len(i[2])-77])
# temp = re.sub(b"^\$ABS/", b'', temp)
# cleaned_cache_db.append([i[0], i[1], temp.decode('utf-8')])

# # get data from storage db
# conn = sqlite3.connect(pathlib.Path(base_dir) / pathlib.Path(storage_file))
# cursor = conn.cursor()
# cursor.execute(select_storage_db)

# array_storage_db = cursor.fetchall()

# # create the csv file with the data
# with open('skype_sent_items_list.csv', 'w', newline='') as csvfile:
# # create csv writer and write the headers into the file
# csv_writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
# csv_writer.writerow(['File path', 'Receiving Skype User', 'Timestamp (UTC)'])
# # map the data form the two databases (could have been done in sql but we do it here)
# for i in cleaned_cache_db:
# for j in array_storage_db:
# if i[2] == j[4]:
# csv_writer.writerow([j[4], j[3],
# datetime.datetime.utcfromtimestamp(i[1]/10000000).strftime('%Y-%m-%d %H:%M:%S')])


def write_csv():
    pass


def process_data(input_file, output_file):
    sql_connect_and_fetch(input_file, check_table_select)


def sql_connect_and_fetch(database, select):
    """
    Connect to database and fetch the data based on the given select statement
    :param database:
    :param select:
    :return:
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute(select)
    return cursor.fetchall()


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
        description="Analyzer for LDB_MainData.db from LG Android devices"
    )

    ap.add_argument(
        "-i", "--input_path", required=True,
        help="Path to the source database")

    ap.add_argument(
        "-f", "--input_file", required=False,
        help="Name of the source database (Default: LDB_MainData.db)",
        default="LDB_MainData.db")

    ap.add_argument(
        "-o", "--output_path", required=True,
        help="Target path to store the results in")

    ap.add_argument(
        "-r", "--output_file", required=False,
        help="Filename of the output file (Default: LDB_MainData.csv)",
        default="LDB_MainData.csv")

    args = ap.parse_args()

    # Create absolute path if necessary
    input_path = create_abs_path(args.input_path)
    output_path = create_abs_path(args.output_path)

    process_data(os.path.join(input_path, args.input_file),
                 os.path.join(output_path, args.output_file))


if __name__ == "__main__":
    main()
