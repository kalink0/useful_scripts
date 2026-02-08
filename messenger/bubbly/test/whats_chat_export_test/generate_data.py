import random
from datetime import datetime, timedelta
from pathlib import Path

# ----------------------
# Configuration
# ----------------------
output_folder = Path("./test_whatsapp_export")  # where the export will go
txt_file_name = "WhatsApp Chat with TestUser.txt"
media_folder_name = "Media"
num_messages = 15000  # adjust for testing lazy loading / search
senders = ["Alice", "Bob", "M."]  # include owner
owner_name = "M."
include_media = True  # include some media messages

media_files = [
    "image1.jpg",
    "image2.png",
    "video1.mp4",
    "audio1.mp3",
    "document1.pdf",
]

# ----------------------
# Create folders
# ----------------------
output_folder.mkdir(exist_ok=True)
(media_path := output_folder / media_folder_name).mkdir(exist_ok=True)

# ----------------------
# Create dummy media files
# ----------------------
for f in media_files:
    path = media_path / f
    if not path.exists():
        path.write_text(f"Dummy content for {f}")

# ----------------------
# Generate messages
# ----------------------
start_time = datetime(2026, 2, 8, 8, 0, 0)
lines = []

for i in range(num_messages):
    sender = random.choice(senders)
    timestamp = (start_time + timedelta(minutes=i)).strftime("%d.%m.%Y, %H:%M")
    content = f"Test message {i+1} from {sender}"

    # Randomly attach media
    media_file = random.choice(media_files + [None, None, None])  # bias to text
    if include_media and media_file:
        content += f" <Anhang: {media_file}>"

    # iOS style: [DD.MM.YYYY, HH:MM] Sender: content
    line = f"[{timestamp}] {sender}: {content}"
    lines.append(line)

# ----------------------
# Write TXT file
# ----------------------
txt_path = output_folder / txt_file_name
with open(txt_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Example WhatsApp export created at {txt_path}")
print(f"Media folder created at {media_path}")
print(f"Total messages: {num_messages}")