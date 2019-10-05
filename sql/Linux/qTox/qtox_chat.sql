/*
 * AUTHOR:         kalink0
 * MAIL:           kalinko@be-binary.de
 * CREATION DATE:  2019/10/05
 *
 * LICENSE:        CC0-1.0
 *
 * SOURCE:         https://github.com/kalink0/useful_scripts/Linux/qTox
 *
 * TITLE:          qtox_chat.sql
 *
 * DESCRIPTION:    Script to parse Chat data out of qTox Messenger database.
 *			Location 	- $HOME/.config/tox/
			Database name 	- [tox_username].db
 *
 *
 * KNOWN RESTRICTIONS:
 *
 *
 * USAGE EXAMPLE:  Execute with e.g. SQlite Browser or SQlite CLI on the sqlite db
 *
 */


SELECT datetime(timestamp/1000, 'unixepoch') as "Timestamp (UTC)",
message as "Message",
chat_id as "Chat ID",
display_name as "Sender Name",
p1.public_key as "Sender ID",
p2.public_key as "Chat Partner ID"
FROM history
INNER JOIN aliases ON aliases.id = history.sender_alias
INNER JOIN peers p1 ON p1.id = owner
INNER JOIN peers p2 ON p2.id = history.chat_id;
