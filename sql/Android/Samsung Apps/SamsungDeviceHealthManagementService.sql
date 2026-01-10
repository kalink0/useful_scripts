-- App: Android Samsung Device Health Management Service
-- Tested App Version: 
-- Creation Date: 2026-01-10
-- Last Modification Date: 2026-01-10
-- Database Location: [...]/com.sec.android.sdhms/databases/
-- Database Name: please see corresponding section for database name specific to SELECT statement
-- Parse Samsung Device Health Management Service App
-- Author: Marco Neumann (kalink0)

-- List Network Usage
-- Data for about the last 5 days
-- If Package Name == -5 -> Whole system data - not app specific
-- Database Name: thermal_log
SELECT
id [ID],
strftime('%Y-%m-%d %H:%M:%S.', "start_time"/1000, 'unixepoch') || ("start_time"%1000) [Start Time],
strftime('%Y-%m-%d %H:%M:%S.', "end_time"/1000, 'unixepoch') || ("end_time"%1000) [End Time],
package_name [Package Name],
uid [Package ID],
net_usage [Network Usage]
FROM NETSTAT