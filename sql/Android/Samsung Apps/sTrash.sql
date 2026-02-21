-- App: Android Samsung Trash Provider
-- Tested App Version: 
-- Creation Date: 2026-02-21
-- Last Modification Date: 2026-02-21
-- Database Location: [...]/com.samsung.android.providers.trash/databases/
-- Database Name: please see corresponding section for database name specific to SELECT statement
-- Parse Samsung Trash Provider
-- Author: Marco Neumann (kalink0)

-- List All Files in Trash
-- Including deleted/trashed Notes
-- Database Name: trash.db
SELECT
    _id [File ID],
    _data [Trash File Path],
    original_path [Original File Path],
    title [File Titel],
    _display_name [File Name],
    _size [File Size],
    mime_type [MIME Type],
    delete_package_name [App Context],
    is_cloud [Cloud?],
    user_id [User ID],
    strftime('%Y-%m-%d %H:%M:%S.', "date_deleted"/1000, 'unixepoch') || ("date_deleted"%1000) [Deletion Timestamp],
    strftime('%Y-%m-%d %H:%M:%S.', "date_expires"/1000, 'unixepoch') || ("date_expires"%1000) [Expiration Timestamp],
    extra [Extra Info JSON]
FROM trashes