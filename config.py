import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OWNER_CHAT_ID = int(os.getenv("OWNER_CHAT_ID", "0"))
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8080").rstrip("/")
WEB_PORT = int(os.getenv("WEB_PORT", "8080"))

WEBDAV_URL = os.getenv("WEBDAV_URL", "")
WEBDAV_USERNAME = os.getenv("WEBDAV_USERNAME", "")
WEBDAV_PASSWORD = os.getenv("WEBDAV_PASSWORD", "")

BACKUP_INTERVAL_HOURS = int(os.getenv("BACKUP_INTERVAL_HOURS", "24"))

DATA_DIR = "/app/data"
IMAGES_DIR = os.path.join(DATA_DIR, "images")
DB_PATH = os.path.join(DATA_DIR, "bot.db")

# 确保目录存在
os.makedirs(IMAGES_DIR, exist_ok=True)