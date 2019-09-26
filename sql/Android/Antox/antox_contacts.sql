/*
 * AUTHOR:         kalink0
 * MAIL:           kalinko@be-binary.de
 * CREATION DATE:  2019/07/27
 *
 * LICENSE:        CC0-1.0
 *
 * SOURCE:         https://github.com/kalink0/useful_scripts/Android/Antox
 *
 * TITLE:          antox_contacts.sql
 *
 * DESCRIPTION:    Script to parse contacts out of Antox Messenger database.
 *			Location	- /data/data/chat.tox.antox/databases
 *			Database name 	- [antox_username].db
 *
 *
 * KNOWN RESTRICTIONS:
 *
 *
 * USAGE EXAMPLE:  Execute with e.g. SQlite Browser or SQlite CLI on the sqlite database
 *
 */


 SELECT tox_key AS "User Key",
 	name AS 'Username',
 	CASE WHEN isblocked is '1'
 		THEN 'Blocked'
 		ELSE 'Not Blocked'
 	END AS 'Blocked Status'
 FROM contacts;
