-- App: Android Samsung Device Health Management Service
-- Tested App Version: 
-- Creation Date: 2026-01-10
-- Last Modification Date: 2026-01-10
-- Database Location: [...]/com.sec.android.sdhms/databases/
-- Database Name: please see corresponding section for database name specific to SELECT statement
-- Parse Samsung Device Health Management Service App
-- Author: Marco Neumann (kalink0)

-- USAGE LOG AND STATS
-- List Network Usage
-- Data for about the last 5 days
-- If Package Name == -5 -> Whole system data - not app specific
-- Database Name: thermal_log
SELECT
strftime('%Y-%m-%d %H:%M:%S.', "start_time"/1000, 'unixepoch') || ("start_time"%1000) [Start Time],
strftime('%Y-%m-%d %H:%M:%S.', "end_time"/1000, 'unixepoch') || ("end_time"%1000) [End Time],
id [ID],
package_name [Package Name],
uid [Package ID],
net_usage [Network Usage]
FROM NETSTAT

-- List Hardware Temperature
-- Data for about the last 5 days
-- Temperature in Celsius but division by 10 required
-- Existing Sensors and used sensors for value dependa on device
-- Database Name: thermal_log
SELECT
strftime('%Y-%m-%d %H:%M:%S.', "timestamp"/1000, 'unixepoch') || ("timestamp"%1000) [Timestamp],
skin_temp/10.0 [Chassis Temperature],
ap_temp/10.0 [Processor Temperature],
bat_temp/10.0 [Battery Temperature],
usb_temp/10.0 [USB Temperature],
chg_temp/10.0 [Charging IC Temperature],
pa_temp/10.0 [Cellular Radio Temperature],
wifi_temp/10.0 [WiFi Temperature]
FROM TEMPERATURE

-- List CPU Usage
-- Data for about the last 5 days
-- Process Usage is about factor 1000 for 100 % of 1 Core, e.g. 1000 = 1 Core by 100 %, 2000 = 2 Cores by 100 %
-- Database Name: thermal_log
SELECT
strftime('%Y-%m-%d %H:%M:%S.', "start_time"/1000, 'unixepoch') || ("start_time"%1000) [Start Time],
strftime('%Y-%m-%d %H:%M:%S.', "end_time"/1000, 'unixepoch') || ("end_time"%1000) [End Time],
uptime [Uptime],
process_name [Process Name],
uid [Package ID],
pid [Process ID],
process_usage [Process Usage]
FROM CPUSTAT