/*
 * AUTHOR:         kalink0
 * MAIL:           kalinko@be-binary.de
 * CREATION DATE:  2019/07/27
 *
 * LICENSE:        CC0-1.0
 *
 * SOURCE:         https://github.com/kalink0/useful_scripts/Android/Freenet_Mail
 *
 * TITLE:          antox_chat.sql
 *
 * DESCRIPTION:    Script to parse Chat data out of Antox Messenger database.
 *			Location 	- /data/data/de.freenet.mail/databases/mail.db
			Database name 	- main.db
 *
 *
 * KNOWN RESTRICTIONS:
 *					Currently the data in the column cc, bcc, from and to are JSON 
 *					objcts that are not decoded. Readable but not the final result
 *
 *
 * USAGE EXAMPLE:  Execute with e.g. SQlite Browser or SQlite CLI on the sqlite db
 *
 */

Select 	"mail"."bcc" as "BCC", 
		"mail"."cc" as "CC", 
		"mail"."email" as "Account",
		"mail"."from" as "From", 
		"mail"."to" as "To", 
		"mail"."subject" as "Subject", 
		"mail_body"."plain" as "Message Plain",  
		"mail_body"."html" as "Message HTML",
		datetime("mail"."send_date", 'unixepoch') as "Date Sent", 
		datetime("mail"."received_date", 'unixepoch') as "Date Received"
From "mail" 
Inner Join "mail_body" On "mail"."_id" = "mail_body"."mail_hash_id"