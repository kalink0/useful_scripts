#!/usr/bin/env python3
#-*- coding: utf-8 -*-
""" 
----------------------------------------------------------------------------------------
 AUTHOR:           kalink0 (kalinko@be-binary.de)
 CREATION DATE:    2026-01-26
 DESCRIPTION:
                   Script to parse WhatsApp Chat Export and create HTML Report 
                   with bubble view linked media

 USAGE EXAMPLES:
                   wa_chat_export_parser.py 
                        --input "./WhatsApp Chat with kalinko.zip" --output output/
                   wa_chat_export_parser.py 
                        --input ./folder/WhatsApp Chat with kalinko.txt" --output output/
                   wa_chat_export_parser.py 
                        --input ./folder --output output/

 ----------------------------------------------------------------------------------------
 """


import re
import argparse
import json
from pathlib import Path
from datetime import datetime
import shutil
import zipfile
import tempfile
import sys
from typing import List, Dict, Optional
import unicodedata

def parse_messages_from_file(file_path):
    """
    Parse WhatsApp export txt file
    """
    messages = []
    current_msg = {}
    timestamp_pattern = re.compile(r"^\d{2}/\d{2}/\d{4}, \d{2}:\d{2} - ")

    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if timestamp_pattern.match(line):
                # Save previous message
                if current_msg:
                    media_file, text = extract_media_file(current_msg["content"])
                    current_msg["media"] = media_file
                    current_msg["content"] = text
                    current_msg["url"] = extract_url(current_msg["content"])
                    messages.append(current_msg)

                # Start new message
                split_index = line.find(" - ")
                timestamp = line[:split_index]
                rest = line[split_index + 3:]
                if ": " in rest:
                    sender, content = rest.split(": ", 1)
                else:
                    sender, content = rest, ""

                current_msg = {
                    "timestamp": timestamp,
                    "sender": sender,
                    "content": content,
                    "media": None,
                    "url": None
                }
            else:
                # Continuation of previous message
                if current_msg:
                    current_msg["content"] += "\n" + line

    # Add last message
    if current_msg:
        media_file, text = extract_media_file(current_msg["content"])
        current_msg["media"] = media_file
        current_msg["content"] = text
        current_msg["url"] = extract_url(current_msg["content"])
        messages.append(current_msg)

    return messages

def extract_media_file(content):
    """
    Extract media file from archive/folder
    The structure needs to be unchanged
    """
    media_extensions = (
        "jpg|jpeg|png|gif|webp|"
        "mp4|mov|webm|3gp|"
        "opus|ogg|mp3|m4a|wav|aac|"
        "pdf"
    )

    media_regex = re.compile(
        rf"""^
        (?P<filename>.+?\.({media_extensions}))
        \s*
        (\(.*\))?
        $
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    lines = content.splitlines()

    if not lines:
        return None, content

    match = media_regex.match(lines[0])
    if match:
        media_file = match.group("filename")
        text = "\n".join(lines[1:]).strip()
        return media_file, text

    return None, content

def extract_media_file_ios(content):
    lines = content.splitlines()
    media_file = None
    cleaned_lines = []

    pattern = re.compile(
        r"<attached:\s*(.+\.(jpg|jpeg|png|gif|webp|mp4|mov|webm|3gp|opus|ogg|mp3|m4a|wav|aac|pdf))\s*>",
        re.IGNORECASE
    )

    for line in lines:
        match = pattern.search(line)
        if match:
            media_file = match.group(1)
            continue  # remove attachment line from text
        cleaned_lines.append(line)

    cleaned_text = "\n".join(cleaned_lines).strip()
    return media_file, cleaned_text


def extract_url(content):
    """
    Parse URLs out of txt
    """
    url_pattern = r"(https?://\S+)"
    match = re.search(url_pattern, content)
    return match.group(1) if match else None

def export_html(messages, input_folder, output_folder, user, case_number, wa_account_name, wa_account_number, chat_name, output_html_name, is_group_chat):
    """
    Create the HTML with bubble view and relative links to attachments
    """
    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    media_folder = output_folder / "media"
    media_folder.mkdir(exist_ok=True)

    # Copy media files
    copied_count = 0
    for msg in messages:
        if msg["media"]:
            src = input_folder / msg["media"]
            if src.exists():
                shutil.copy(src, media_folder / msg["media"])
                copied_count += 1
            else:
                print(f"Warning: media file missing: {msg['media']}")

    # Header
    generated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header_html = f"""
    <div class="report-header" style="padding:10px; margin-bottom:20px; background:#ddd; border-radius:10px;">
        <p><strong>Report generated by:</strong> {user}</p>
        <p><strong>Report generated at:</strong> {generated_time}</p>
        <p><strong>Case number:</strong> {case_number}</p>
        <p><strong>WhatsApp account name:</strong> {wa_account_name}</p>
        <p><strong>WhatsApp account number:</strong> {wa_account_number}</p>
        <p><strong>Chat/Contact name:</strong> {chat_name}</p>
        <p><strong>Media files copied:</strong> {copied_count}</p>
    </div>
    """

    html_lines = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='UTF-8'><title>Chat Export</title>",
        "<style>",
        "body { font-family: Arial, sans-serif; background: #f0f0f0; }",
        ".chat { max-width: 800px; margin: auto; padding: 20px; }",
        ".bubble { padding: 10px 15px; margin: 5px 0; border-radius: 15px; display: inline-block; max-width: 70%; }",
        ".timestamp { font-size: 0.8em; color: #666; margin-top: 5px; }",
        ".media { margin-top: 5px; }",
        "img { max-height: 150px; border-radius: 10px; }",
        "video { max-width: 100%; border-radius: 10px; }",
        "audio { max-width: 100%; margin-top: 5px; display: block; }",
        ".clear { clear: both; }",
        ".left { background: #e0e0e0; float: left; clear: both; color: black; }",
        ".right { background: #4CAF50; color: white; float: right; clear: both; }",
        ".owner { float: right; background: #4CAF50; color: white; border: 2px solid #FFD700; }",
        ".other { float: left; background: #e0e0e0; color: black; }",
        "</style></head><body>",
        header_html,
        "<div class='chat'>"
    ]

    # For 1-on-1 chats, keep alternating bubbles
    participant_colors = {}

    for msg in messages:
        # Determine bubble class and sender label
        is_owner = msg["sender"] == wa_account_name
        if is_group_chat:
            bubble_class = "owner" if is_owner else "other"
        else:
            if msg["sender"] not in participant_colors:
                participant_colors[msg["sender"]] = "left" if len(participant_colors) % 2 == 0 else "right"
            bubble_class = participant_colors[msg["sender"]]

        # Sender label (always add (owner) if it's the owner)
        sender_html = f"<span class='sender'><strong>{msg['sender']}" + (" (owner)" if is_owner else "") + "</strong></span>"

        media_html = ""
        if msg["media"]:
            media_path = Path("media") / msg["media"]
            ext = media_path.suffix.lower()
            if ext in [".jpg", ".jpeg", ".png", ".gif"]:
                media_html = f'<div class="media"><a href="{media_path}"><img src="{media_path}"></a></div>'
            elif ext in [".mp4", ".webm", ".mov"]:
                media_html = f'<div class="media"><video controls src="{media_path}"></video></div>'
            elif ext in [".mp3", ".m4a", ".wav", ".aac", ".opus", ".ogg"]:
                media_html = f'<div class="media"><audio controls src="{media_path}"></audio></div>'
            else:
                media_html = f'<div class="media"><a href="{media_path}">{msg["media"]}</a></div>'
        elif msg["url"]:
            media_html = f'<div class="media"><a href="{msg["url"]}">{msg["url"]}</a></div>'

        html_lines.append(f"<div class='bubble {bubble_class}'>")
        html_lines.append(sender_html)
        html_lines.append(msg['content'].replace("\n", "<br>"))
        if media_html:
            html_lines.append(media_html)
        html_lines.append(f"<div class='timestamp'>{msg['timestamp']}</div>")
        html_lines.append("</div><div class='clear'></div>")

    html_lines.append("</div></body></html>")

    output_html_path = output_folder / output_html_name
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_lines))

    print(f"HTML saved to {output_html_path} with relative media folder.")

def read_messages(folder_path):
    """
    Get alle the messages from the txt
    """
    folder_path = Path(folder_path)
    txt_files = list(folder_path.glob("*.txt"))
    if not txt_files:
        raise FileNotFoundError(f"No .txt file found in {folder_path}")

    all_messages = []
    for txt_file in txt_files:
        messages = parse_messages_from_file(txt_file)
        all_messages.extend(messages)

    return all_messages, folder_path

def read_messages_ios(input_path):
    input_path = Path(input_path)

    # Pick TXT file
    if input_path.is_dir():
        txt_files = list(input_path.glob("*.txt"))
        if not txt_files:
            raise FileNotFoundError(f"No .txt file found in folder {input_path}")
        txt_file = txt_files[0]
    else:
        txt_file = input_path

    folder_path = txt_file.parent

    with open(txt_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    messages: List[Dict] = []

    current_msg: Optional[Dict] = None

    for line in lines:
        line = "".join(c for c in line if unicodedata.category(c)[0] != "C").strip()
        if not line:
            continue

        if line.startswith("["):  # new message
            # Append previous message if exists
            if current_msg:
                messages.append(current_msg)

            # Extract timestamp
            try:
                ts_end = line.index("]")
                timestamp = line[1:ts_end].strip()
                rest = line[ts_end + 1:].strip()
            except ValueError:
                timestamp = ""
                rest = line

            # Extract sender up to first colon
            if ":" in rest:
                sender, content = rest.split(":", 1)
                sender = sender.strip()
                content = content.strip()
            else:
                sender = rest
                content = ""

            # Create new message
            current_msg = {
                "timestamp": timestamp,
                "sender": sender,
                "content": content,
                "media": None,
                "url": None
            }

            # Immediately extract media for this message only
            media_file, text = extract_media_file_ios(current_msg["content"])
            current_msg["media"] = media_file
            current_msg["content"] = text

        else:  # continuation line
            if current_msg:
                current_msg["content"] += "\n" + line
                # Re-extract media for updated content
                media_file, text = extract_media_file_ios(current_msg["content"])
                current_msg["media"] = media_file
                current_msg["content"] = text

    # Append last message
    if current_msg:
        messages.append(current_msg)

    return messages, folder_path


def extract_zip(zip_path):
    """
    If its a zip, handle it
    """
    temp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    return temp_dir

def extract_chat_name(path):
    """
    Extract chat or group name from folder or filename.
    Everything after 'with ' is considered chat name, preserving spaces and special characters.
    """
    name = path.name  # use full filename/folder name
    if "with " in name:
        chat_part = name.split("with ", 1)[1]
        # Remove extension if present
        if chat_part.lower().endswith(".txt") or chat_part.lower().endswith(".zip"):
            chat_part = chat_part.rsplit(".", 1)[0]
        return chat_part.strip()
    return name.strip()

def extract_chat_name_ios(file_path):
    """
    Extract chat name from iOS WhatsApp export.
    Uses everything after the FIRST '-' in the filename.
    """
    name = file_path.stem  # strip .txt
    if "-" in name:
        # Split at first dash
        parts = name.split("-", 1)
        chat_name = parts[1].strip()
    else:
        chat_name = name.strip()
    return chat_name

def sanitize_filename(name):
    """
    Remove any not allowed chars
    """
    return re.sub(r'[<>:"/\\|?*]', '_', name)


def main():
    """
    Here it begins
    """
    parser = argparse.ArgumentParser(description="WhatsApp Chat Export parser with HTML report")
    parser.add_argument("--input", help="Path to folder, zip, or TXT with WhatsApp export")
    parser.add_argument("--output", help="Output folder or file path")
    parser.add_argument("--platform", choices=["android", "ios"], help="Is the export from Android or from iOS? (android/ios)")
    parser.add_argument("--user", help="User generating the report")
    parser.add_argument("--case", help="Case number")
    parser.add_argument("--wa-name", help="WhatsApp account name")
    parser.add_argument("--wa-number", help="WhatsApp account number")
    parser.add_argument("--group-chat", choices=["yes", "no"], help="Is this a group chat? (yes/no)")
    args = parser.parse_args()

    # Load config.json if exists
    script_folder = Path(sys.argv[0]).parent
    config = {}
    config_path = script_folder / "config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                print(f"Loaded config from {config_path}")
        except json.JSONDecodeError as e:
            print(f"Warning: Could not read config.json: {e}")

    # Handle the inputs
    input_path = Path(args.input or config.get("input") or input("Enter path to folder, zip, or TXT: ").strip())

    if not input_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    if input_path.is_dir():
        folder_path = input_path
    elif input_path.suffix.lower() == ".zip":
        folder_path = extract_zip(input_path)
    elif input_path.suffix.lower() == ".txt":
        folder_path = input_path.parent  # use parent folder for media path
    else:
        raise ValueError("Input must be a folder, ZIP file, or a TXT export")

    

    user = args.user or config.get("user") or input("Enter your name: ").strip()
    case_number = args.case or config.get("case_number") or input("Enter case number: ").strip()
    # wa_account_name is used to identify owner of device - if empty, no owner can be identified - parser still works
    wa_account_name = args.wa_name or config.get("wa_name") or input("Enter WhatsApp account name: ").strip()
    wa_account_number = args.wa_number or config.get("wa_number") or input("Enter WhatsApp account number: ").strip()

    # ask for group chat - if yes put owner on right side - everyone else to the left
    if args.group_chat:
        is_group_chat = args.group_chat.lower() == "yes"
    else:
        is_group_chat_input = input("Is this a group chat? (yes/no, default no): ").strip().lower()
        is_group_chat = is_group_chat_input == "yes"

    # Get the messages and media

    platform = args.platform or config.get("platform") or input("Enter source platform (android/ios): ").strip()
    if platform == 'android':
        messages, folder_path = read_messages(folder_path)
        chat_name = extract_chat_name(input_path)
    elif platform == 'ios':
        messages, folder_path = read_messages_ios(folder_path)
        chat_name = extract_chat_name_ios(input_path)
    else:
        raise ValueError("No valid source platform given!")
   
    # Generating HTML output
    chat_name_safe = sanitize_filename(chat_name)
    case_number_safe = sanitize_filename(case_number)

    output_folder = Path(args.output or f"{case_number_safe}_{chat_name_safe}")
    output_html_name = f"{case_number_safe}_{chat_name_safe}.html"

    export_html(
        messages,
        folder_path,
        output_folder,
        user,
        case_number,
        wa_account_name,
        wa_account_number,
        chat_name,
        output_html_name,
        is_group_chat
    )

    # clean the temp files when we worked with zip
    if input_path.suffix.lower() == ".zip":
        shutil.rmtree(folder_path)

if __name__ == "__main__":
    main()
