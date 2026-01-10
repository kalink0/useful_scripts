-- App: Android Samsung Honeyboard
-- Tested App Version: 5.9.20.89
-- Creation Date: 2026-01-10
-- Last Modification Date: 2026-01-10
-- Database Location: [...]/com.samsung.android.honeyboard/
-- Database Name: please see corresponding section for database name specific to SELECT statement
-- Parse Samsung Honeyboard App
-- Author: Marco Neumann (kalink0)

-- List Clip Items (Copied texts)
-- About last 30 days in the database
-- Images copied are in the folder .../clipboard, subfolder is in epoch timestamp - no database existent
-- Database Name: ClipItem.db
SELECT 
strftime('%Y-%m-%d %H:%M:%S.', "time_stamp"/1000, 'unixepoch') || ("time_stamp"%1000) [Clip Date],
text [Content],
caller_package_name [App Context],
user_id [User Context]
FROM clip_table

-- List Removed Word Suggestions
-- Database Name: RemoveListManager
SELECT
added_time [Added Time],
word [Deleted Word],
locale [Related Locale]
FROM RemovedList