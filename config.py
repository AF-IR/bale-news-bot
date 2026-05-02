import os
from dotenv import load_dotenv

load_dotenv()


def get_env(key: str, default: str = "", var_type: type = str):
    value = os.getenv(key, default)
    
    if var_type == bool:
        return value.lower() in ("true", "1", "yes", "on")
    elif var_type == int:
        try:
            return int(value)
        except (ValueError, TypeError):
            return int(default) if default else 0
    return value


# ─────────────────────────────────────────
# تنظیمات اصلی
# ─────────────────────────────────────────
BOT_TOKEN = get_env("BOT_TOKEN", "")
ADMIN_ID = get_env("ADMIN_ID", "0", int)
CHANNEL_ID = get_env("CHANNEL_ID", "0", int)

# ─────────────────────────────────────────
# تبلیغات
# ─────────────────────────────────────────
AD_ENABLED = get_env("AD_ENABLED", "true", bool)
AD_LINK = get_env("AD_LINK", "@GoldChi")

# ─────────────────────────────────────────
# تنظیمات خبر
# ─────────────────────────────────────────
NEWS_INTERVAL = get_env("NEWS_INTERVAL", "15", int)
MAX_NEWS_PER_FETCH = get_env("MAX_NEWS_PER_FETCH", "15", int)

# ─────────────────────────────────────────
# دیتابیس
# ─────────────────────────────────────────
DB_FILE = "bot_database.json"
NEWS_CACHE_FILE = "sent_news.json"

# ─────────────────────────────────────────
# منبع خبری (فقط مهر)
# ─────────────────────────────────────────
RSS_FEEDS = [
    {"name": "مهر", "url": "https://www.mehrnews.com/rss"},
]

# ─────────────────────────────────────────
# اعتبارسنجی
# ─────────────────────────────────────────
def validate_config():
    errors = []
    if not BOT_TOKEN:
        errors.append("❌ BOT_TOKEN تنظیم نشده")
    if not CHANNEL_ID or CHANNEL_ID == 0:
        errors.append("❌ CHANNEL_ID تنظیم نشده")
    return len(errors) == 0, errors
