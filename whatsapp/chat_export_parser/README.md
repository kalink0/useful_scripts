# WhatsApp Chat Export Parser

Parses Chat Export from WhatsApp - relys on the structure of this export.
Generates the result as HTML report - with bubble view and media attachments.

## Tested with following version:
2.26.2.72, english language

## Supported Format:

1. Original ZIP-File that is exported by WhatsApp
2. Unpacked ZIP - Original Structure (either the folder or directly txt is given)


## USAGE EXAMPLE:
ZIP-File:  wa_chat_export_parser.py --input ./WhatsApp\ Chat\ with\ kalinko.zip --output output/
TXT:  wa_chat_export_parser.py --input ./folder/WhatsApp\ Chat\ with\ kalinko.txt --output output/
Folder: wa_chat_export_parser.py --input ./folder --output output/

You can also create a config.json with parameters

Additionally values like Report generator, case number, WA Account NAme and WA account number are asked by the script.
The value of WA Account name is used to identify the owner of the device from where the chat was exported from.
Without the correct value here the script will still show all bubbles and related media - but without the owner info.

### Group Chats
For group chat the script is not able to detect a group chat. The user of this script can
give the script the hint, that it is a group chat - so the script will handle the bubble view better.
Default of chat type is 1-to-1.

## Resctriction:

1. Only reads ONE ChatExport per run
2. Will overwrite existing media files in target folder!! So one folder per chat necessary!!
3. The chat Name is read from the zip/folder name OR the txt name. Currently it splits by
the word "with" - everything after it will be set as Chat name. This only work in english.
If wiht is not found the full file name will be set as Chat/contact name.
4. Also the time stamp is based on the english timestamp - there is more work to do 
for other languages