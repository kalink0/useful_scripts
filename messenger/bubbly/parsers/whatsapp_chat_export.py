from pathlib import Path
from typing import List, Dict, Tuple, Optional
import re
import unicodedata

class WhatsAppChatExportParser:
    """
    Parser for WhatsApp chat exports (iOS + Android)
    """

    # ----------------------
    # Public method
    # ----------------------
    def parse(
        self,
        input_folder: Path,
        media_folder: Path,
        platform: str,
        wa_account_name: str,
        wa_account_number: str,
        is_group_chat: bool,
        **kwargs
    ) -> Tuple[List[Dict], Dict]:
        """
        Generic parse entry point for BubblyLauncher
        Returns:
            messages: list of dicts (sender, content, timestamp, media, url, is_owner)
            metadata: dict for BubblyExporter header
        """
        input_folder = Path(input_folder)

        if platform.lower() == "ios":
            messages = self._parse_ios(input_folder)
        elif platform.lower() == "android":
            messages = self._parse_android(input_folder)
        else:
            raise ValueError(f"Unsupported platform: {platform}")

        # Determine is_owner for each message
        for msg in messages:
            msg["is_owner"] = msg["sender"] == wa_account_name

        # Build metadata for header
        metadata = {
            "user": kwargs.get("user"),
            "case": kwargs.get("case"),
            "chat_name": kwargs.get("chat_name"),
            "source": "WhatsApp",
            "wa_account_name": wa_account_name,
            "wa_account_number": wa_account_number,
            "is_group_chat": is_group_chat,
            "platform": platform
        }

        return messages, metadata

    # ----------------------
    # iOS parser
    # ----------------------
    def _parse_ios(self, input_folder: Path) -> List[Dict]:
        # Find TXT file
        txt_files = list(input_folder.glob("*.txt"))
        if not txt_files:
            raise FileNotFoundError(f"No .txt file found in {input_folder}")
        txt_file = txt_files[0]

        with open(txt_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        messages: List[Dict] = []
        current_msg: Optional[Dict] = None

        for line in lines:
            # Remove control characters
            line = "".join(c for c in line if unicodedata.category(c)[0] != "C").strip()
            if not line:
                continue

            if line.startswith("["):  # New message
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

                # Extract sender and content
                if ":" in rest:
                    sender, content = rest.split(":", 1)
                    sender = sender.strip()
                    content = content.strip()
                else:
                    sender = rest
                    content = ""

                media_file, content = self._extract_media_file_ios(content)

                current_msg = {
                    "timestamp": timestamp,
                    "sender": sender,
                    "content": content,
                    "media": media_file,
                    "url": None
                }
            else:  # Continuation
                if current_msg:
                    current_msg["content"] += "\n" + line
                    media_file, content = self._extract_media_file_ios(current_msg["content"])
                    current_msg["media"] = media_file
                    current_msg["content"] = content

        if current_msg:
            messages.append(current_msg)

        return messages

    # ----------------------
    # Android parser
    # ----------------------
    def _parse_android(self, input_folder: Path) -> List[Dict]:
        txt_files = list(input_folder.glob("*.txt"))
        if not txt_files:
            raise FileNotFoundError(f"No .txt file found in {input_folder}")
        txt_file = txt_files[0]

        messages = []
        current_msg = {}
        timestamp_pattern = re.compile(r"^\d{2}/\d{2}/\d{4}, \d{2}:\d{2} - ")

        with open(txt_file, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if timestamp_pattern.match(line):
                    # Save previous message
                    if current_msg:
                        media_file, text = self._extract_media_file(current_msg["content"])
                        current_msg["media"] = media_file
                        current_msg["content"] = text
                        current_msg["url"] = self._extract_url(current_msg["content"])
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
                    if current_msg:
                        current_msg["content"] += "\n" + line

        if current_msg:
            media_file, text = self._extract_media_file(current_msg["content"])
            current_msg["media"] = media_file
            current_msg["content"] = text
            current_msg["url"] = self._extract_url(current_msg["content"])
            messages.append(current_msg)

        return messages

    # ----------------------
    # Media extraction iOS
    # ----------------------
    def _extract_media_file_ios(self, content: str):
        lines = content.splitlines()
        media_file = None
        cleaned_lines = []

        pattern = re.compile(
            r"<\s*(?:Anhang|attached):\s*(-?.+?\.(?:jpg|jpeg|png|gif|webp|mp4|mov|webm|3gp|opus|ogg|mp3|m4a|wav|aac|pdf))\s*>",
            re.IGNORECASE
        )

        for line in lines:
            match = pattern.search(line)
            if match:
                media_file = match.group(1)
                continue
            cleaned_lines.append(line)

        return media_file, "\n".join(cleaned_lines).strip()

    # ----------------------
    # Media extraction Android
    # ----------------------
    def _extract_media_file(self, content: str):
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

    # ----------------------
    # URL extraction
    # ----------------------
    def _extract_url(self, content: str) -> Optional[str]:
        url_pattern = re.compile(r"https?://\S+")
        match = url_pattern.search(content)
        if match:
            return match.group(0)
        return None
