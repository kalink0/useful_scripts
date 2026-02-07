-- App: LinkedIn
-- Tested App Version: 4.1.966, 4.1.1166
-- Creation Date: 2026-02-07
-- Last Modification Date: 2026-02-07
-- Database Location: [...]/com.linkedin.android/databases/
-- Database Name: please see corresponding section for database name specific to SELECT statement
-- Parse Messages of LinkedIn Apps
-- Author: Marco Neumann (kalink0)

-- MESSAGES
-- Database Name: messenger-sdk
SELECT
strftime('%Y-%m-%d %H:%M:%S.', "md"."deliveredAt"/1000, 'unixepoch') || ("md"."deliveredAt"%1000) [deliveredAt],
CASE WHEN md.status = '5' 
    THEN 'Delivered'
    ELSE 'Unknown'
END[Status],
json_extract(pd.entityData, '$.participantType.member.firstName.text') [sender_firstname],
json_extract(pd.entityData, '$.participantType.member.lastName.text') [sender_lastname],
json_extract(pd.entityData, '$.participantType.member.headline.text') [sender_headline],
json_extract(pd.entityData, '$.participantType.member.profileUrl') [sender_profile_url],
json_extract(pd.entityData, '$.participantType.member.distance') [sender_distance],
json_extract(md.entityData, '$.subject') [subject],
json_extract(md.entityData, '$.body.text') [message],
md.conversationUrn [conversationUrn]
FROM MessagesData md
JOIN ConversationsData cd ON cd.entityUrn = md.conversationUrn
LEFT JOIN ParticipantsData pd on pd.entityUrn = md.senderUrn