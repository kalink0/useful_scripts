-- App: Android ROMEO - Gay Dating
-- App Version: 3.28.3
-- Creation Date: 2025-11-16
-- Last Modification Date: 2025-11-16
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
json_extract(location, '$.long') [Longitude]
FROM accounts
