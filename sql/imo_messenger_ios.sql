/*
 * AUTHOR:         kalink0
 * MAIL:           kalinko@be-binary.de
 * CREATION DATE:  2018/12/03
 *
 * LICENSE:        CC0-1.0
 *
 * SOURCE:         https://github.com/kalink0/useful_scripts
 *
 * TITLE:          imo_messenger_io.sql
 *
 * DESCRIPTION:    Script to parse Chat data out of imo messenger database
 *
 *
 * KNOWN RESTRICTIONS:
 *                 Column names are in German for readability in Germany. Can be changed easily.
 *
 * USAGE EXAMPLE:  Execute with e.g. SQlite Browser or SQlite CLI on the sqlite file IMODb2_1.sqlite
 * 
 */


SELECT  MSG.ZBUID as 'User ID',
		CON.ZDISPLAY as 'Anzeigename',
		CON.ZALIAS as 'Alias',
		CON.ZPHONE as 'Telefonnummer',
		MSG.ZTEXT as 'Nachricht', 
		datetime((MSG.ZTS / 1000000000), 'unixepoch') as 'Zeitstempel (UTC)', 
		CASE WHEN MSG.ZISSENT is '1' 
			THEN 'Gesendet'
			ELSE 'Empfangen'
		END as 'Typ'
FROM ZIMOCHATMSG as MSG
LEFT JOIN ZIMOCONTACT as CON ON CON.ZBUID = MSG.ZBUID;