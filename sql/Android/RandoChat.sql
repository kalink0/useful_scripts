-- App: Android App RandoChat
-- Tested App Version: 6.3.3
-- Creation Date: 2026-01-15
-- Last Modification Date: 2026-01-15
-- Database Location: [...]/com.random.chat.app/databases/
-- Database Name: please see corresponding section for database name specific to SELECT statement
-- Parse Android Random Chat App
-- Author: Marco Neumann (kalink0)

-- ACCOUNT
-- Database Name: ramdochatV2.db
SELECT 
MAX(CASE WHEN name LIKE 'apelido' THEN value END) [Username],
MAX(CASE WHEN name LIKE 'sexo' THEN (CASE WHEN value = 'H' THEN 'Male' WHEN value = 'M' THEN 'Female' END) END) [User Sex],
MAX(CASE WHEN name LIKE 'idade' THEN value END) [User Age],
MAX(CASE WHEN name LIKE 'language' THEN value END) [Language],
MAX(CASE WHEN name LIKE 'device_id' THEN value END) [Device ID],
MAX(CASE WHEN name LIKE 'idade_de' THEN value END) [Preferred Age From],
MAX(CASE WHEN name LIKE 'idade_ate' THEN value END) [Preferred Age To],
MAX(CASE WHEN name LIKE 'sexo_search' THEN (CASE WHEN value = 'H' THEN 'Male' WHEN value = 'M' THEN 'Female' END) END) [Preferred Sex]
FROM configuracao

-- CONTACTS
-- Database Name: ramdochatV2.db
SELECT
c.id_pessoa [Account ID],
c.apelido [Username],
c.idade [Age],
CASE
	WHEN c.sexo = 'M' THEN 'Female' -- From Mulher
	WHEN c.sexo = 'H' THEN 'Male'  -- From Homem
END	[Sex],
CASE
	WHEN c.favorite = 1 THEN 'Yes'
	WHEN c.favorite = 0 THEN 'No'
END [Favorite?],
CASE
	WHEN c.bloqueado = 1 THEN 'Yes'
	WHEN c.bloqueado = 0 THEN 'No'
END [Blocked?],
CASE WHEN
	c.images = '' THEN 'n/a'
ELSE
	json_extract(c.images, "$[0].img")
END [Link Profile Pic]
FROM conversa c

-- MESSAGES
-- Database Name: ramdochatV2.db
SELECT
strftime('%Y-%m-%d %H:%M:%S.', "hora"/1000, 'unixepoch') || ("hora"%1000) [Timestamp (UTC)],
m.mensagem [Message Content],
CASE
WHEN m.minha = 2 THEN 'Received'
WHEN m.minha = 1 THEN 'Sent'
END [Direction],
c.apelido [Contact Username],
m.url [Media File],
m.id_talk_server [Conversation ID],
m.id_servidor [Message ID]
FROM mensagens m
LEFT JOIN conversa c ON c.id_server = m.id_talk_server