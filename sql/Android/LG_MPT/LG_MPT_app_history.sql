/*
 * AUTHOR:         kalink0
 * MAIL:           kalinko@be-binary.de
 * CREATION DATE:  2019/10/27
 *
 * LICENSE:        CC0-1.0
 *
 * SOURCE:         https://github.com/kalink0/useful_scripts/Android/LG_MPT
 *
 * TITLE:          LG_MPT_app_history.sql
 *
 * DESCRIPTION:    Script to get App history out of LG MPT logging database
 *			Location 		- /mpt/
			Database name 	- LDB_MainData.db
 *
 *
 * KNOWN RESTRICTIONS:
 *                Meaning of values in the columns f007, f008 and 009 unknown
 *
 * USAGE EXAMPLE:  Execute with e.g. SQlite Browser or SQlite CLI on the sqlite db
 *
 */

 SELECT
 f001 AS "ID",
 DATETIME(f002/1000, 'unixepoch') AS "Timestamp (UTC)",
 f003 AS "App Path",
 f004 AS "App Version",
 DATETIME(f005/1000, 'unixepoch') AS "Original Install Date",
 DATETIME(f006/1000, 'unixepoch') AS "Deletion Date"
 FROM t305;
