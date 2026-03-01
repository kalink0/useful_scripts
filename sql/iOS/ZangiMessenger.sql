
-- App: iOS App Zangi Messenger
-- Tested App Version: 5.6.7
-- Creation Date: 2026-03-01
-- Last Modification Date: 2026-03-01
-- Database Location: [...]/AppGroup/<PackageID>/
-- Database Name: please see corresponding section for database name specific to SELECT statement
-- Parse iOS Zangi Messenger App
-- Author: Marco Neumann (kalink0)

-- ACCOUNT
-- Database Name: zangidb_<account_id>.sqlite
SELECT
strftime('%Y-%m-%d %H:%M:%S.', "ZSTATUSLASTSYNCTIME"/1000, 'unixepoch') || ("ZSTATUSLASTSYNCTIME"%1000) [Last Sync Time],
ZNUMBER [Account ID],
ZNICKNAME [Account Name],
ZLASTNAME [Last Name],
ZNAME [First Name],ZNICKNAME [Account Name],
ZNEWPASSCODE [Passcode],
ZPASSWORD [Password],
ZPINCODE [PIN Code],
ZSHAREDHIDECONVERSATIONPIN [HIDE CONVERSATION PIN],
ZUSEREMAIL [Account Mail],
ZSTATUS [Account Status],
ZUSERREGSTATUS [Registration Status],
ZCOUNTRY [Country]
FROM ZUSER

-- CONTACTS
-- Database Name: zangidb_<account_id>.sqlite
SELECT
datetime('2001-01-01', "zc"."ZMODIFICATIONDATE" || ' seconds') [Last Modification Timestamp],
datetime("zcn"."ZLASTACTIVITY", 'unixepoch') [Last Activity Timestamp],
zc.ZLASTNAME [Last Name],
zc.ZFIRSTNAME [First Name],
zc.ZDISPLAYNAME [Display Name],
zcn.ZFULLNUMBER [Contact Number],
zcn.ZEMAIL [Contact Mail],
zcnt.ZNAME [Registration Number Type],
zc.ZIDENTIFIRE [Contact Identifier],
zc.ZISBLOCKED [Blocked?],
zcn.ZISFAVORITE [Favorite?]
FROM ZCONTACT zc
LEFT JOIN Z_4CONTACTNUMBER z4cn ON zc.Z_PK = z4cn.Z_4CONTACT
LEFT JOIN ZCONTACTNUMBER zcn ON zcn.Z_PK = z4cn.Z_5CONTACTNUMBER
LEFT JOIN ZCONTACTNUMBERTYPE zcnt ON zcnt.Z_PK = zc.Z_PK