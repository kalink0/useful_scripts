/*
 * AUTHOR:         kalink0
 * MAIL:           kalinko@be-binary.de
 * CREATION DATE:  2019/10/27
 *
 * LICENSE:        CC0-1.0
 *
 * SOURCE:         https://github.com/kalink0/useful_scripts/Android/LG_MPT
 *
 * TITLE:          LG_MPT_gapp_detail_multimedia.sql
 *
 * DESCRIPTION:    Script to get App usage info for multimedia out of LG MPT logging database
 *			Location 		- /mpt/
			Database name 	- LDB_MainData.db
 *
 *
 * KNOWN RESTRICTIONS:
 *
 * USAGE EXAMPLE:  Execute with e.g. SQlite Browser or SQlite CLI on the sqlite db
 *
 */

SELECT
f001 AS "ID",
DATETIME(f002/1000, 'unixepoch') AS "Timestamp (UTC)",
f003 AS "App Path",
f004 AS "App Name",
f005 AS "Called Method",
f007 AS "Parameter"
FROM t432;
