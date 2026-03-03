
-- App: iOS App Zangi Messenger
-- Tested App Version: 5.6.7
-- Creation Date: 2026-03-01
-- Last Modification Date: 2026-03-03
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


-- MESSAGES
-- Database Name: zangidb_<account_id>.sqlite
SELECT
    datetime('2001-01-01', "zm"."ZMESSAGETIME" || ' seconds') [Message Timestamp],
    zm.ZMESSAGEID [Message ID],
    zm.ZMESSAGE [Message Text],
    CASE
        WHEN grp.Z_PK IS NOT NULL THEN 'Group'
        ELSE 'Direct'
    END [Conversation Type],
CASE zm.ZTYPE
    WHEN 0   THEN 'Text'
    WHEN 1   THEN 'Image/Media'
    WHEN 2   THEN 'Video'
    WHEN 3   THEN 'Location'
    WHEN 4   THEN 'Voice note'
    WHEN 8   THEN 'Link/Share'
    WHEN 9   THEN 'File/Document'
    WHEN 101 THEN 'System message'
    WHEN 115 THEN 'Group event'
    WHEN 160 THEN 'Call start'
    WHEN 175 THEN 'Call end'
    ELSE 'Other/Unknown'
END [Message Type],
    
COALESCE(
    NULLIF(grp.ZUID, ''),
    NULLIF(cnv.ZGROUPUID, ''),
    CAST(cnv.ZUID AS TEXT)
) [Conversation ID],

COALESCE(
    NULLIF(TRIM(gpf.ZNAME), ''),
    NULLIF(TRIM(cnv.ZGROUPNAME), ''),
    NULLIF(TRIM(chat_ct.ZDISPLAYNAME), ''),
    NULLIF(TRIM(COALESCE(chat_ct.ZFIRSTNAME, '') || ' ' || COALESCE(chat_ct.ZLASTNAME, '')), ''),
    chat_cn.ZFULLNUMBER,
    CAST(cnv.ZUID AS TEXT)
) [Chat Name],

COALESCE(
    NULLIF(TRIM(snd_ct.ZDISPLAYNAME), ''),
    NULLIF(TRIM(COALESCE(snd_ct.ZFIRSTNAME, '') || ' ' || COALESCE(snd_ct.ZLASTNAME, '')), ''),
    snd_cn.ZFULLNUMBER,
    CAST(zm.ZFROM AS TEXT)
) [Sender Name],
snd_cn.ZFULLNUMBER [Sender Number],
CASE
    WHEN zm.ZISRECEIVED = 0 THEN 'Outgoing'
    WHEN zm.ZISRECEIVED = 1 THEN 'Incoming'
    ELSE 'Unknown'
END [Direction],
COALESCE(
    NULLIF(zm.ZFILEREMOTEPATH, ''),
    NULLIF(zm.ZMEDIAASSETSLIBRARYURL, ''),
    NULLIF(zm.ZENCRYPTFILEREMOTEPATH, '')
) [Media Path],
zm.ZFILEEXTENSION [Media Extension]

FROM ZZANGIMESSAGE zm
LEFT JOIN ZCONVERSATION cnv         ON cnv.Z_PK = zm.ZCONVERSATION
LEFT JOIN ZGROUP grp                ON grp.ZCONVERSATION = cnv.Z_PK
LEFT JOIN ZGROUPPROFILE gpf         ON gpf.ZGROUP = grp.Z_PK

LEFT JOIN ZCONTACTNUMBER snd_cn     ON snd_cn.Z_PK = zm.ZFROM
LEFT JOIN Z_4CONTACTNUMBER snd_lnk  ON snd_lnk.Z_5CONTACTNUMBER = snd_cn.Z_PK
LEFT JOIN ZCONTACT snd_ct           ON snd_ct.Z_PK = snd_lnk.Z_4CONTACT

LEFT JOIN ZCONTACTNUMBER chat_cn    ON chat_cn.Z_PK = cnv.ZMEMBER
LEFT JOIN Z_4CONTACTNUMBER chat_lnk ON chat_lnk.Z_5CONTACTNUMBER = chat_cn.Z_PK
LEFT JOIN ZCONTACT chat_ct          ON chat_ct.Z_PK = chat_lnk.Z_4CONTACT;