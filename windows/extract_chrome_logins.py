# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# AUTHOR:         kalink0
# MAIL:           kalinko@be-binary.de
# CREATION DATE:  2018/07/14
#
# LICENSE:        CC0-1.0
#
# SOURCE:         https://github.com/kalink0/useful_scripts
#
# TITLE:          extract_chrome_logins.py
#
# DESCRIPTION:    Extract login data from chrome browser.
#
#
# KNOWN RESTRICTIONS:
#				  The Python module pywin32 is required, that is normally not brought by python default packages.
#				  Only usable on Windows
#				  There must not be any active running Chrome instance
#
# USAGE EXAMPLE:  python extract_chrome_logins.py
#
#-------------------------------------------------------------------------------

import argparse
import datetime
import os
import csv
from pathlib import Path
import sqlite3
import win32crypt

# Dictionary to store the logins per url
logins = {}

def connect_to_sql(login_db):
	# TODO: Also get the timestamps last use and convert them
	# Connect to the db and query the necessary data
	connection = sqlite3.connect(login_db)
	cursor = connection.cursor()
	select_statement = "SELECT origin_url, username_value, password_value, date_created FROM logins"
	cursor.execute(select_statement)
	login_data = cursor.fetchall()
	return login_data

def prepare_data(login_data):
	global logins
	for url, user_name, pwd, epoch in login_data:
		password = decrypt_password(pwd)
		timestamp = transform_timestamp(epoch)
		logins[url] = (user_name, password[1], timestamp)

def decrypt_password(pwd):
	return win32crypt.CryptUnprotectData(pwd, None, None, None, 0)

def transform_timestamp(epoch):
    return datetime.datetime(1601,1,1) + datetime.timedelta(microseconds=int(epoch))

def print_logins():
	# Print the credentials to stdout
	for url, login in logins.items():
		print (url + " " + str(login[0]) + " " + login[1].decode('utf-8') + " " + str(login[2]))

def create_csv_with_logins(dest, output_name):
	d = os.path.join(dest, output_name)
	with open(d, 'w',  newline='') as csv_file:
		csv_writer = csv.writer(csv_file, delimiter = ',', quotechar='"', quoting=csv.QUOTE_ALL)
		csv_writer.writerow(['URL', 'Username', 'Password', 'Created'])
		for url, login in logins.items():
			csv_writer.writerow ( [url, str(login[0]), login[1].decode('utf-8'), login[2]] )
	print ("===== Results written to: " + d + "=====")

def get_current_time():
	now = datetime.datetime.now()
	return (now.strftime("%Y%m%d-%H%M%S"))

if __name__ == "__main__":
	# define and parse cli arguments
	parser = argparse.ArgumentParser(description='Extract Login data from Chrome Browser.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument("-d" ,"--dest", help="Destination folder of output file", default='.')
	parser.add_argument("-o" ,"--output_name", help="File name of output file", default="chrome_export_" + os.environ['COMPUTERNAME'] + '_' + get_current_time() + '.csv')
	args = parser.parse_args()
	# Set chrome path -> HOME\AppData\Local\Google\Chrome\User Data\Default
	chrome_path = os.path.join(str(Path.home()), 'AppData', 'Local', 'Google', 'Chrome', 'User Data', 'Default')
	# Set Path to the sqlite db with stored login data
	login_db = os.path.join(chrome_path, 'Login Data')
	login_data = connect_to_sql(login_db)
	prepare_data(login_data)
	print_logins()
	create_csv_with_logins(args.dest, args.output_name)
