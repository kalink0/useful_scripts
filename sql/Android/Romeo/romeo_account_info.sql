-- App: Android ROMEO - Gay Dating
-- App Version: 3.28.3
-- Database Location: data\data\com.planetromeo.android.app\databases\
-- Parse ROMEO Accounts Infos
-- Author: Marco Neumann (kalink0)


SELECT 
_id [ID],
username [Username],
email [E-Mail],
json_extract(location, '$.address.address') [Addresse],
json_extract(location, '$.name') [Ort],
json_extract(location, '$.lat') [Breitengrad],
json_extract(location, '$.long') [Längengrad]
FROM accounts
