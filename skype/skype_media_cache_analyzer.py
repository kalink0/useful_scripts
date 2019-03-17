# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# AUTHOR:         kalink0
# MAIL:           kalinko@be-binary.de
# CREATION DATE:  2019/01/15
#
# LICENSE:        CC0-1.0
#
# SOURCE:         https://github.com/kalink0/useful_scripts
#
# TITLE:          skype_media_cache_analyzer
#
# DESCRIPTION:   Script to analyze the media cache from Skype (up to Version 7).
#                The Script extracts the original paths of files, that were sent via Skype
#                Including the timestamp and the receiving Skype user.
#                This script should be used in the case that all information in the main.db was deleted from the tables
#                messages and MediaDocuments  and is not recoverable.
#                The script creates a csv file with the results.
#
# KNOWN RESTRICTIONS:
#                You don't get all sent media files.
#                This scripts needs more double checking of the results!
#
# USAGE EXAMPLE:  python extract_chrome_logins.py
#
# -------------------------------------------------------------------------------


import sqlite3
import pathlib
import re
import datetime
import csv

# set this value with your pass to the media_messaging folder
base_dir = "c:\path_to_skype_app_data\media_messaging"
# relative paths to database files
cache_file = "media_cache_v3/asyncdb/cache_db.db"
storage_file = "storage_db/asyncdb/storage_db.db"

# list to store the necessary values from the sqlite after they are minimized
cleaned_cache_db = []
# select statement to execute on cache db
select_cache_db = "select key, access_time, serialized_data from assets;"
# select statement to execute on storage db
select_storage_db = "select documents.id, uri, file_name, user_name, local_path " \
                    "from documents " \
                    "inner join document_permissions on document_permissions.id = documents.id " \
                    "inner join contents on contents.id = document_permissions.id;"

conn = sqlite3.connect(pathlib.Path(base_dir) / pathlib.Path(cache_file))
cursor = conn.cursor()
cursor.execute(select_cache_db)

# store the data from the table into a multi-dim array
array_cache_db = cursor.fetchall()

# Header, first variant, 12 bytes long
header = "\x04\x00\x00\x00I\x00\x00\x00I\x00\x00\x00"
# Footer; 77 bytes long
footer = "\x01\x00\x00\x00\x01\x04\x00\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x03\x00\x00\x00\x04\x00\x00\x00\x02" \
         "\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
         "\x00\x08\x00\x00\x00\x97\xf6\x9dX\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"

# delete all entries that leads to a media_cache file. We cannot use them to trace sending/receiving.
# remove unnecessary rows
regex = re.compile(b"i\d{4}|\$CACHE")
cleaned_array = [i for i in array_cache_db if not regex.search(i[2])]
# we don't need the original one anymore, so let's delete it
del array_cache_db[:]

# now lets remove the header and footer in the encoded field so we can create a default string with the
# content to get the path
for i in cleaned_array:
    temp = (i[2][12:len(i[2])-77])
    temp = re.sub(b"^\$ABS/", b'', temp)
    cleaned_cache_db.append([i[0], i[1], temp.decode('utf-8')])

# get data from storage db
conn = sqlite3.connect(pathlib.Path(base_dir) / pathlib.Path(storage_file))
cursor = conn.cursor()
cursor.execute(select_storage_db)

array_storage_db = cursor.fetchall()

# create the csv file with the data
with open('skype_sent_items_list.csv', 'w', newline='') as csvfile:
    # create csv writer and write the headers into the file
    csv_writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
    csv_writer.writerow(['File path', 'Receiving Skype User', 'Timestamp (UTC)'])
    # map the data form the two databases (could have been done in sql but we do it here)
    for i in cleaned_cache_db:
        for j in array_storage_db:
            if i[2] == j[4]:
                csv_writer.writerow([j[4], j[3],
                                     datetime.datetime.utcfromtimestamp(i[1]/10000000).strftime('%Y-%m-%d %H:%M:%S')])
