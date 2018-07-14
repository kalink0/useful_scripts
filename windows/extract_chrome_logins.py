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
# DESCRIPTION:    Extract 
#
#
# KNOWN RESTRICTIONS:
#				  The Python module pywin32 is required, that is normally not brought by python default packages.
#				  Only usable on Windows	
#
# USAGE EXAMPLE:  python extract_chrome_logins.py
#
#-------------------------------------------------------------------------------

import os
import csv
from pathlib import Path
import sqlite3
import win32crypt

# Set chrome path -> HOME\AppData\Local\Google\Chrome\User Data\Default
chrome_path = os.path.join(str(Path.home()), 'AppData', 'Local', 'Google', 'Chrome', 'User Data', 'Default')
# Set Path to the sqlite db with stored login data
login_db = os.path.join(chrome_path, 'Login Data')

# TODO: Also get the timestamps last use and convert them
# Connect to the db and query the necessary data
connection = sqlite3.connect(login_db)
cursor = connection.cursor()
select_statement = "SELECT origin_url, username_value, password_value FROM logins"
cursor.execute(select_statement)
login_data = cursor.fetchall()

# Dictionary to store the logins per url
logins = {}

# Decrytping the passwords
for url, user_name, pwd in login_data:
	password = win32crypt.CryptUnprotectData(pwd, None, None, None, 0)
	logins[url] = (user_name, password[1])

# Print the credentials to the stdout
for url, login in logins.items():
	print (url + " " + str(login[0]) + " " + login[1].decode('utf-8'))

# Create csv
# TODO: Make the file name changeable or at least combine it with current time and pc-name
with open('chrome_passwords.csv', 'w',  newline='') as csv_file:
	csv_writer = csv.writer(csv_file, delimiter = ',', quotechar='"', quoting=csv.QUOTE_ALL)
	csv_writer.writerow(['URL', 'Username', 'Password'])
	for url, login in logins.items():
		csv_writer.writerow ( [url, str(login[0]), login[1].decode('utf-8')] )
