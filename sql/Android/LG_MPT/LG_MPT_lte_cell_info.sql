/*
 * AUTHOR:         kalink0
 * MAIL:           kalinko@be-binary.de
 * CREATION DATE:  2019/10/27
 *
 * LICENSE:        CC0-1.0
 *
 * SOURCE:         https://github.com/kalink0/useful_scripts/Android/LG_MPT
 *
 * TITLE:          LG_MPT_lte_cell_info.sql
 *
 * DESCRIPTION:    Script to get LTE Cell info out of LG MPT logging database
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
 f006 AS "Cell ID",
 f005 AS "LAC",
 f003 AS "MCC",
 f004 AS "MNC"
 FROM t330;
