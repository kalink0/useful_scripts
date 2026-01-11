-- App: Android Samsung Notes
-- Tested App Version: 4.4.30.91
-- Creation Date: 2026-01-11
-- Last Modification Date: 2026-01-11
-- Database Location: [...]/com.samsung.android.app.notes/databases/
-- Database Name: please see corresponding section for database name specific to SELECT statement
-- Parse Samsung Notes
-- Author: Marco Neumann (kalink0)

-- List All Notes
-- Including deleted/trashed Notes
-- For file path -> Docs and attachments are stored at least two times - in data/user/0/<app> and in data/data/<app>. But in hte data/data path addtional the subfolder "mainlist" exists
-- The Attachments are listed in one cell per row, CSV inside -> path,size,created_timestamp,isdeleted
-- Database Name: sdoc.db
SELECT
strftime('%Y-%m-%d %H:%M:%S.', "sd"."createdAt"/1000, 'unixepoch') || ("sd"."createdAt"%1000) [Creation Timestamp],
strftime('%Y-%m-%d %H:%M:%S.', "sd"."lastModifiedAt"/1000, 'unixepoch') || ("sd"."lastModifiedAt"%1000) [Last Modification Timestamp],
sd.title [Title],
sd.content [Text Content],
sd.isDeleted [Deleted?],
strftime('%Y-%m-%d %H:%M:%S.', "sd"."recycle_bin_time_moved"/1000, 'unixepoch') || ("sd"."recycle_bin_time_moved"%1000) [Recycle Bin Timestamp],
strftime('%Y-%m-%d %H:%M:%S.', "sd"."firstOpendAt"/1000, 'unixepoch') || ("sd"."firstOpendAt"%1000) [First Opened Timestamp],
strftime('%Y-%m-%d %H:%M:%S.', "sd"."secondOpenedAt"/1000, 'unixepoch') || ("sd"."secondOpenedAt"%1000) [Second Opened Timestamp],
strftime('%Y-%m-%d %H:%M:%S.', "sd"."lastOpenedAt"/1000, 'unixepoch') || ("sd"."lastOpenedAt"%1000) [Last Opened Timestamp],
GROUP_CONCAT('"' || cn._data || '"' || ',' || '"' || cn.size || '"' || ',' || '"' || cn.createdAt || '"' || ',' || '"' || cn.isDeleted || '"', CHAR(10)) [Attachments]
FROM sdoc sd
LEFT JOIN content cn ON sd.UUID = cn.sdocUUID
GROUP BY sd.UUID