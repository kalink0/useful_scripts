/*
 * AUTHOR:         kalink0
 * MAIL:           kalinko@be-binary.de
 * CREATION DATE:  2019/10/27
 *
 * LICENSE:        CC0-1.0
 *
 * SOURCE:         https://github.com/kalink0/useful_scripts/Android/LG_MPT
 *
 * TITLE:          LG_MPT_gapp_detail_wifi_connection.sql
 *
 * DESCRIPTION:    Script to get Wifi connection info for undefined apps out of LG MPT logging database
 *			Location 		- /mpt/
			Database name 	- LDB_MainData.db
 *
 *
 * KNOWN RESTRICTIONS:
 *                IN the column f004 (Status) there are multiple values divided
 *                by pipes. Parsing of them individually is not done yet
 *                The meaning of the value in column f003 is not known yet
 *
 * USAGE EXAMPLE:  Execute with e.g. SQlite Browser or SQlite CLI on the sqlite db
 *
 */

 SELECT
 f001 AS "ID",
 DATETIME(f002/1000, 'unixepoch') AS "Timestamp (UTC)",
 f003 AS "Unknown Value",
 f004 AS "Status"
 FROM t601;
