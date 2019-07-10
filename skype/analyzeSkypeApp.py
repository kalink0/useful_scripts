# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# AUTHOR:         kalink0
# MAIL:           kalinko@be-binary.de
# CREATION DATE:  2019/07/09
#
# LICENSE:        CC0-1.0
#
# SOURCE:         https://github.com/kalink0/useful_scripts
#
# TITLE:          analyzeSkypeApp
#
# DESCRIPTION:   This script extracts the file names of the media cache files from
#				 the databases cache_db.db and skype.db.
#				 A csv. file is created with the file name, date and time of send/receive
#				 and the sender/receiver.
#				 One than can look up the file names in the folder media_cache_v3 and knows
#				 if the file there was sent or received via Skype.
#
# KNOWN RESTRICTIONS:
#                Currently only Tested with SkypeApp Version 14.40.70.0 on Windows 10.
#				  
#
# USAGE EXAMPLE:  python analyzeSkypeApp.py
#
# -------------------------------------------------------------------------------


import sqlite3
import pathlib
import re
import datetime
import csv

# set the path to the Skype folder of the Skype Account
base_dir = "PATH_TO_SKYPE_PROFILE"
# relative paths to database files from the skype profile path / base_dir
media_cache_folder = "media_messaging/media_cache_v3/"
cache_db = media_cache_folder + "asyncdb/cache_db.db"
skype_db = "skype.db"

# list to store the necessary values from the sqlite after they are minimized
cleaned_cache_db = []
# select statement to execute on cache db
select_cache_db = "select key, serialized_data from assets;"
# select statement to execute on skype db
select_skype_db = 	"select conversations.id as 'Conversation Partner', author as 'Sender'," \
					"originalarrivaltime as 'Time Received', content " \
					"from messages " \
					"inner join conversations on conversations.dbid = messages.convdbid;"

conn = sqlite3.connect(pathlib.Path(base_dir) / pathlib.Path(cache_db))
cursor = conn.cursor()
cursor.execute(select_cache_db)

# store the data from the table into a multi-dim array
array_cache_db = cursor.fetchall()
conn.close()

# Regex for getting the file name out of the serialized_data field.
regex = re.compile(b"\$CACHE\/\\\\\\\\(\S+)\\x01\\x00")
count = 0
for i in array_cache_db:

	result = regex.search(i[1])
	if result:
		#print (result.group(1))
		i = i + (result.group(1).decode('utf-8'),)
		#print (i)
		array_cache_db[count] = (i)
	count = count + 1


## Get data out of skype.db and prepare it
conn = sqlite3.connect(pathlib.Path(base_dir) / pathlib.Path(skype_db))
cursor = conn.cursor()
cursor.execute(select_skype_db)
array_skype_db = []
array_skype_db = cursor.fetchall()

# Get URL out of Content field and add it to the tuple as last field
# Regex to get the URL of the image file
regex = re.compile("uri=\"(\S+)\"")
count = 0
for i in array_skype_db:

	result = regex.search(i[3])
	if result:
		i = i + (result.group(1),)
		array_skype_db[count] = (i)
	count = count + 1

# create the csv file with the data
with open('pic_to_chat.csv', 'w', newline='', encoding='utf-8') as csvfile:
	# create csv writer and write the headers into the file
	csv_writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
	csv_writer.writerow(['Chat Partner', 'Sender', 'Timestamp (UTC)', 'File Name'])
	# map the data from the two databases (could have been done in sql but we do it here)
	for skype in array_skype_db:
		for cache in array_cache_db:
			if len(skype) == 5 and len(cache) == 3:
				if cache[0] == 'u' + skype[4]:
					csv_writer.writerow([skype[0], skype[1],
										datetime.datetime.utcfromtimestamp(skype[2]/1000).strftime('%Y-%m-%d %H:%M:%S'),
										cache[2]])
