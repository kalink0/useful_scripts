-- App: Android ROMEO - Gay Dating
-- App Version: 3.28.3
-- Creation Date: 2025-11-16
-- Last Modification Date: 2026-02-25
-- Database Location: data\data\com.planetromeo.android.app\databases\
-- Database Name: accounts.db
-- Parse ROMEO Accounts Infos
-- Author: Marco Neumann (kalink0)


SELECT 
_id [ID],
username [Username],
email [E-Mail],
json_extract(location, '$.address.address') [Address],
json_extract(location, '$.name') [City],
json_extract(location, '$.lat') [Latitude],
json_extract(location, '$.long') [Longitude],
json_extract(profile, '$.headline') [Headline],
json_extract(profile, '$.personal.profile_text') [Profile Text],
json_extract(profile, '$.creation_date') [Creation Date],
json_extract(profile, '$.last_login') [Last Login],
json_extract(profile, '$.personal.age') [Age],
json_extract(profile, '$.personal.birthdate') [Birthdate]
FROM accounts
