/*
 * AUTHOR:         kalink0
 * MAIL:           kalinko@be-binary.de
 * CREATION DATE:  2019/08/19
 *
 * LICENSE:        CC0-1.0
 *
 * SOURCE:         https://github.com/kalink0/useful_scripts/Android/Romeo
 *
 * TITLE:         romeo_chat_android.sql
 *
 * DESCRIPTION:    Script to parse contacts out of Antox Messenger database.
 *			Location	- /data/data/com.planetromeo.android.app/db/
 *			Database name 	- [romeo_id].db
 *
 *
 * KNOWN RESTRICTIONS:
 *
 *
 * USAGE EXAMPLE:  Execute with e.g. SQlite Browser or SQlite CLI on the sqlite database
 *
 */

Select MESSAGES.date As "Datum (UTC)",
  MESSAGES.to_id As "Empfänger ID",
  MESSAGES.from_id As "Sender ID",
  USERS.name As Empfänger,
  USERS1.name As Sender,
  MESSAGES."text" As Nachricht
From MESSAGES
  Inner Join USERS On MESSAGES.to_id = USERS._id
  Inner Join USERS USERS1 On MESSAGES.from_id = USERS1._id