-- App: Android ROMEO - Gay Dating
-- App Version: 3.28.3
-- Creation Date: 2025-11-16
-- Last Modification Date: 2025-11-16
-- Database Location: data\data\com.planetromeo.android.app\databases\
-- Database Name: planetromeo-room.db.<userid>
-- Parse ROMEO Messages Info
-- Author: Marco Neumann (kalink0)

SELECT me.date [Timestamp]
, me.chatPartnerId [Contact ID], cpe.name [Contact Name]
, me.text [Message Text]
, me.transmissionStatus [Status], me.saved [Saved?], me.unread [Unread?]
, me.messageId [Message ID]
, CASE WHEN iae.imageId IS NOT NULL
	THEN
	"Ja"
	ELSE
	"Nein"
END [Image Contained?]
FROM MessageEntity me
INNER JOIN ChatPartnerEntity cpe ON cpe.profileId = me.chatPartnerId
LEFT JOIN ImageAttachmentEntity iae ON me.messageId = iae.parentMessageId