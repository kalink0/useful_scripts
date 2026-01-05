-- App: Android Samsung My Files
-- App Version: x
-- Creation Date: 2026-01-04
-- Last Modification Date: 2026-01-04
-- Database Location: [...]\com.sec.android.app.myfiles\databases\
-- Database Name: please see corresponding section for database name specific to SELECT statement
-- Parse Samsung My Files App
-- Author: Marco Neumann (kalink0)


-- OPERATION HISTORY
-- Database Name: OperationHistory.db

-- List Operations Overview
-- Database Name: OperationHistory.db
SELECT
mDate [Operation Date],
_id [Operation ID],
mOperationType [Operation Type],
mItemCount [# of Items],
mFolderCount [# of Folder],
mPageType [Page Type],
mOperationResult [Result]
FROM operation_history oh

-- List Operations with Details
-- Database Name: OperationHistory.db
SELECT
oh.mdate [Operation Date],
ohd.operation_id [Operation ID],
ohd.src_path [Source Path],
ohd.src_file_id [Source File ID],
ohd.dst_path [Destination Path],
ohd.dst_file_id [Destination File ID],
oh.mOperationType [Operation Type],
oh.mItemCount [# of Items],
oh.mFolderCount [# of Folders],
oh.mPageType [Page Type],
oh.mOperationResult [Result],
oh.mMemoryFullCapacity [Storage Capacity Info]
FROM operation_history_data ohd
JOIN operation_history oh ON oh._id = ohd.operation_id

-- List Favorite Files
-- Database Name: FileInfo.db
SELECT
strftime('%Y-%m-%d %H:%M:%S.', "date_modified"/1000, 'unixepoch') || ("date_modified"%1000) [Date Added],
file_id [File ID],
path [File Path],
name [File Name],
mime_type [File Type],
size [File Size],
is_trashed [Trashed?],
is_hidden [Hidden?]
FROM favorites

-- List Last Search Terms
-- Only the last ten are stored
-- Database Name: FileInfo.db
SELECT
strftime('%Y-%m-%d %H:%M:%S.', "date_modified"/1000, 'unixepoch') || ("date_modified"%1000) [Date Searched],
name [Search Term]
FROM search_history

-- List Recent Files
-- Only stored for the last 30 days
-- Database Name: FileInfo.db
SELECT
strftime('%Y-%m-%d %H:%M:%S.', "recent_date"/1000, 'unixepoch') || ("recent_date"%1000) [Last Date],
strftime('%Y-%m-%d %H:%M:%S.', "date_modified"/1000, 'unixepoch') || ("date_modified"%1000) [Modification Date],
file_id [File ID],
path [File Path],
name [File Name],
mime_type [File Type],
package_name [App Context],
is_download [Download?],
is_hidden [Hidden?],
is_trashed [Trashed?]

FROM recent_files