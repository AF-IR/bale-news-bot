#!/usr/bin/env python3
"""
ربات خبرخوان بله - نسخه GitHub Actions
هر روز یکبار اجرا می‌شود
"""

import time
import logging
import sys
from typing import Optional, List

import requests

import config
from database import Database
from news_fetcher import NewsFetcher, NewsCache

# تنظیم لاگینگ
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("BaleBot")


class BaleBot:
    """کلاس ربات بله"""
    
    BASE_URL = "https://tapi.bale.ai"
    
    def __init__(self, token: str):
        self.token = token
        self.api_url = f"{self.BASE_URL}/bot{token}"
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "BaleBot/1.0",
        })
    
    def _request(self, method: str, data: dict = None) -> Optional[dict]:
        url = f"{self.api_url}/{method}"
        try:
            response = self.session.post(url, json=data or {}, timeout=30)
            result = response.json()
            
            if result.get("ok"):
                return result.get("result")
            else:
                logger.error(f"خطای API: {result}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"خطای شبکه: {e}")
            return None
        except Exception as e:
            logger.error(f"خطا: {e}")
            return None
    
    def get_me(self) -> Optional[dict]:
        return self._request("getMe")
    
    def send_message(self, chat_id: int, text: str) -> bool:
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        result = self._request("sendMessage", data)
        return result is not None


def send_news(bot, db, news_fetcher, news_cache):
    """ارسال اخبار"""
    logger.info("📰 دریافت اخبار از مهر...")
    
    news_items = news_fetcher.fetch_all()
    db.increment_stat("total_news_fetched", len(news_items))
    
    if not news_items:
        logger.warning("⚠️ هیچ خبری دریافت نشد")
        return 0
    
    sent_count = 0
    
    for news in news_items:
        if not news_cache.is_sent(news.id):
            # فرمت پیام بدون لینک و منبع
            ad_line = f"📢 {config.AD_LINK}" if config.AD_ENABLED else ""
            message = news.format_message(ad=ad_line)
            
            result = bot.send_message(config.CHANNEL_ID, message)
            if result:
                news_cache.mark_sent(news.id)
                db.increment_stat("total_messages_sent")
                sent_count += 1
                logger.info(f"✅ {news.title[:50]}...")
                time.sleep(3)  # فاصله بین ارسال‌ها
            else:
                logger.error(f"❌ خطا در ارسال")
    
    db.update_last_news_time()
    logger.info(f"✅ {sent_count} خبر ارسال شد")
    return sent_count


def main():
    """تابع اصلی"""
    
    print("=" * 50)
    print("🤖 ربات خبرخوان مهر")
    print("=" * 50)
    
    # بررسی تنظیمات
    valid, errors = config.validate_config()
    if not valid:
        for error in errors:
            print(error)
        sys.exit(1)
    
    print(f"📢 کانال: {config.CHANNEL_ID}")
    print(f"📢 تبلیغ: {config.AD_LINK}")
    print("=" * 50)
    
    # ایجاد نمونه‌ها
    db = Database(config.DB_FILE)
    news_fetcher = NewsFetcher(config.RSS_FEEDS, config.MAX_NEWS_PER_FETCH)
    news_cache = NewsCache(config.NEWS_CACHE_FILE)
    bot = BaleBot(config.BOT_TOKEN)
    
    # بررسی اتصال
    me = bot.get_me()
    if not me:
        print("❌ خطا در اتصال!")
        sys.exit(1)
    
    print(f"✅ ربات: @{me.get('username', 'N/A')}")
    print("-" * 50)
    
    # ارسال اخبار
    send_news(bot, db, news_fetcher, news_cache)
    
    print("-" * 50)
    print("✅ عملیات تمام شد")


if __name__ == "__main__":
    main()
