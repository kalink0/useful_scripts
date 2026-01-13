-- App: Android ChatGPT
-- Tested App Version: 4.4.30.91
-- Creation Date: 2026-01-11
-- Last Modification Date: 2026-01-11
-- Database Location: [...]/com.openai.chatgpt/databases/
-- Database Name: please see corresponding section for database name specific to SELECT statement
-- Parse ChatGPT
-- Author: Marco Neumann (kalink0)

-- List All messages
-- Media content not handled
-- Database Name: <account_user_id>_conversations.db (e.g. user-wUGKENETKMAjdnE36FJF_f9b1f5cd-5ffd-4d69-a4ff-939a5a0_conversations.db)

SELECT
JSON_EXTRACT(chunk, '$.created_date') [Creation Date],
JSON_EXTRACT(chunk, '$.conversation_id') [Conversation ID],
JSON_EXTRACT(chunk, '$.content.content') [Message Content],
JSON_EXTRACT(chunk, '$.role') [Sender],
JSON_EXTRACT(chunk, '$.id') [Message ID]
from DBMessageChunk
WHERE JSON_VALID(chunk) = 1