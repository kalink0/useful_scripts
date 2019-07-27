/*
 * AUTHOR:         kalink0
 * MAIL:           kalinko@be-binary.de
 * CREATION DATE:  2019/07/27
 *
 * LICENSE:        CC0-1.0
 *
 * SOURCE:         https://github.com/kalink0/useful_scripts/iOS/Antox
 *
 * TITLE:          antox_chat.sql
 *
 * DESCRIPTION:    Script to parse Chat data out of Antox Messenger database.
 *								 Location 			- /data/data/chat.tox.antox/databases
 *								 Database name 	- [antox_username].db
 *
 *
 * KNOWN RESTRICTIONS:
 *
 *
 * USAGE EXAMPLE:  Execute with e.g. SQlite Browser or SQlite CLI on the sqlite file IMODb2_1.sqlite
 *
 */


SELECT timestamp AS 'TimeStamp (UTC)',
 	sender_name AS 'Sent From Username',
 	sender_key AS 'Sent From User_Key',
 	message AS ' Message Content',
 	CASE WHEN has_been_read is '1'
 		THEN 'Read'
 		ELSE 'Unread'
 	END AS 'Reading Status',
 	CASE WHEN has_been_received is '1'
 		THEN 'Message received'
 		ELSE 'Message not recieved'
 	END AS 'Receiving Status',
 	CASE WHEN successfully_sent is '1'
 		THEN 'Message sent'
 		ELSE 'Message not sent'
 	END	AS 'Sending Status'
FROM messages;
