-- App: Android Samsung Gallery 3D 
-- Tested App Version: 15.7.00.43
-- Creation Date: 2026-01-09
-- Last Modification Date: 2026-01-09
-- Database Location: [...]/com.sec.android.gallery3d/databases/
-- Database Name: please see corresponding section for database name specific to SELECT statement
-- Parse Samsung Gallery 3D App
-- Author: Marco Neumann (kalink0)

-- List Trashed Files
-- Default: 31 days in Trash
-- Database Name: Local.db
SELECT
strftime('%Y-%m-%d %H:%M:%S.', "__deleteTime"/1000, 'unixepoch') || ("__deleteTime"%1000) [Delete Time],
__Title [Trash File Name],
__absPath [Trash Path],
__originTitle [Original File Name],
__originPath [Original File Name],
__expiredPeriod [Days to keep],
strftime('%Y-%m-%d %H:%M:%S.', json_extract(__restoreExtra, '$.__dateTaken')/1000, 'unixepoch') || (json_extract(__restoreExtra, '$.__dateTaken')%1000) [Original Taken Time],
json_extract(__restoreExtra, '$.__fileDuration') [File Duration],
json_extract(__restoreExtra, '$.__mimeType') [File Type],
json_extract(__restoreExtra, '$.__size') [File Size],
json_extract(__restoreExtra, '$.__latitude') [Latitude],
json_extract(__restoreExtra, '$.__longitude') [Longitude]
FROM trash