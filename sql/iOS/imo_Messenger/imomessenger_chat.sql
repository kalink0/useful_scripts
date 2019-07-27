/*
 * AUTHOR:         kalink0
 * MAIL:           kalinko@be-binary.de
 * CREATION DATE:  2018/12/03
 *
 * LICENSE:        CC0-1.0
 *
 * SOURCE:         https://github.com/kalink0/useful_scripts/iOS/imo_Messenger
 *
 * TITLE:          imo_messenger.sql
 *
 * DESCRIPTION:    Script to parse Chat data out of imo messenger database
 * 
 *
 * KNOWN RESTRICTIONS:
 *                 
 *
 * USAGE EXAMPLE:  Execute with e.g. SQlite Browser or SQlite CLI on the sqlite file IMODb2_1.sqlite
 * 
 */


SELECT  MSG.ZBUID as 'User ID',
		CON.ZDISPLAY as 'Displayed Name',
		CON.ZALIAS as 'Alias',
		CON.ZPHONE as 'Phone Number',
		MSG.ZTEXT as 'Message Content', 
		datetime((MSG.ZTS / 1000000000), 'unixepoch') as 'Timestamp (UTC)', 
		CASE WHEN MSG.ZISSENT is '1' 
			THEN 'Sent'
			ELSE 'Received'
		END as 'Type'
FROM ZIMOCHATMSG as MSG
LEFT JOIN ZIMOCONTACT as CON ON CON.ZBUID = MSG.ZBUID;