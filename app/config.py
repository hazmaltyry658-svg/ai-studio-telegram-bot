import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "").strip()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/bot.sqlite3")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

MAX_VIDEO_SECONDS = int(os.getenv("MAX_VIDEO_SECONDS", "8"))
MAX_AUDIO_MINUTES = int(os.getenv("MAX_AUDIO_MINUTES", "2"))

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

VIDEO_MODEL = "google/veo-2"
MUSIC_MODEL = "music_v2_5"

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("ضع TELEGRAM_BOT_TOKEN في متغيرات البيئة")
