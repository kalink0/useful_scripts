-- App: Android ROMEO - Gay Dating
-- App Version: 3.28.3
-- Creation Date: 2025-11-16
-- Last Modification Date: 2025-11-16
-- Database Location: data\data\com.planetromeo.android.app\databases\
-- Database Name: planetromeo-room.db.<userid>
-- Parse ROMEO Contacts Info
-- Author: Marco Neumann (kalink0)

SELECT 
ce.userId [UserID], cpe.name [Name], cpe.headline [Headline]
, ce.contactNote [Notiz], ce.linkStatus [Status]
, cpe.age [Age], cpe.weight [Weight], cpe.height [Height]
, cpe.locationName [Ort], cpe.country [Country]
, CASE WHEN cpe.deletionDate IS NOT NULL
	THEN
	strftime('%Y-%m-%d %H:%M:%S.', "cpe"."deletionDate"/1000, 'unixepoch') || ("cpe"."deletionDate"%1000) 
	ELSE
	0
END [Deletion Date]
, cpe.isDeactivated [Deactivated?]
, cpe.isBLocked [Blocked?]

, CASE WHEN cpe.fetchDate IS NOT NULL
	THEN
	strftime('%Y-%m-%d %H:%M:%S.', "cpe"."fetchDate"/1000, 'unixepoch') || ("cpe"."fetchDate"%1000) 
	ELSE
	0
END [Last Fetched Date]
FROM ContactEntity ce
INNER JOIN ChatPartnerEntity cpe ON ce.userID = cpe.profileId