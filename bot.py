#!/usr/bin/env python3
"""
ربات خبرخوان مهر - نسخه دیباگ
"""

import time
import logging
import sys
from datetime import datetime

import requests

import config
from database import Database
from news_fetcher import NewsFetcher, NewsCache

# لاگینگ کامل
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("BaleBot")


class BaleBot:
    BASE_URL = "https://tapi.bale.ai"
    
    def __init__(self, token: str):
        self.token = token
        self.api_url = f"{self.BASE_URL}/bot{token}"
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "BaleBot/1.0",
        })
    
    def _request(self, method: str, data: dict = None) -> dict:
        url = f"{self.api_url}/{method}"
        logger.debug(f"Request: {method}")
        
        try:
            response = self.session.post(url, json=data or {}, timeout=30)
            result = response.json()
            logger.debug(f"Response: {result}")
            
            if result.get("ok"):
                return result.get("result", {})
            else:
                logger.error(f"API Error: {result}")
                return {}
                
        except Exception as e:
            logger.error(f"Request Error: {e}")
            return {}
    
    def get_me(self) -> dict:
        return self._request("getMe")
    
    def send_message(self, chat_id: int, text: str) -> bool:
        logger.info(f"ارسال به {chat_id}: {text[:50]}...")
        
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        
        result = self._request("sendMessage", data)
        
        if result:
            logger.info(f"✅ ارسال موفق")
            return True
        else:
            logger.error(f"❌ ارسال ناموفق")
            return False


def send_news(bot, db, news_fetcher, news_cache):
    logger.info("=" * 50)
    logger.info("📰 شروع دریافت اخبار...")
    
    news_items = news_fetcher.fetch_all()
    logger.info(f"📊 {len(news_items)} خبر دریافت شد")
    
    if not news_items:
        logger.warning("⚠️ هیچ خبری دریافت نشد!")
        return 0
    
    sent_count = 0
    
    for i, news in enumerate(news_items, 1):
        logger.info(f"--- خبر {i}/{len(news_items)} ---")
        logger.info(f"عنوان: {news.title[:60]}")
        logger.info(f"ID: {news.id}")
        logger.info(f"تکراری: {news_cache.is_sent(news.id, news.title)}")
        
        if not news_cache.is_sent(news.id, news.title):
            ad_line = f"📢 {config.AD_LINK}" if config.AD_ENABLED else ""
            message = news.format_message(ad=ad_line)
            
            logger.info(f"متن پیام:\n{message[:200]}...")
            
            if bot.send_message(config.CHANNEL_ID, message):
                news_cache.mark_sent(news.id, news.title)
                db.increment_stat("total_messages_sent")
                sent_count += 1
                time.sleep(3)
        else:
            logger.info("⏭️ تکراری - رد شد")
    
    db.update_last_news_time()
    logger.info(f"✅ {sent_count} خبر ارسال شد")
    return sent_count


def main():
    print("=" * 50)
    print("🤖 ربات خبرخوان مهر - دیباگ")
    print("=" * 50)
    
    # نمایش تنظیمات
    logger.info(f"BOT_TOKEN: {config.BOT_TOKEN[:20]}...")
    logger.info(f"CHANNEL_ID: {config.CHANNEL_ID}")
    logger.info(f"AD_LINK: {config.AD_LINK}")
    logger.info(f"AD_ENABLED: {config.AD_ENABLED}")
    logger.info(f"MAX_NEWS: {config.MAX_NEWS_PER_FETCH}")
    logger.info(f"RSS_URL: {config.RSS_FEEDS[0]['url']}")
    
    # بررسی تنظیمات
    valid, errors = config.validate_config()
    if not valid:
        for error in errors:
            logger.error(error)
        sys.exit(1)
    
    # ایجاد نمونه‌ها
    db = Database(config.DB_FILE)
    news_fetcher = NewsFetcher(config.RSS_FEEDS, config.MAX_NEWS_PER_FETCH)
    news_cache = NewsCache(config.NEWS_CACHE_FILE)
    bot = BaleBot(config.BOT_TOKEN)
    
    # بررسی ربات
    me = bot.get_me()
    if not me:
        logger.error("❌ خطا در اتصال!")
        sys.exit(1)
    
    logger.info(f"✅ ربات: @{me.get('username')}")
    logger.info("=" * 50)
    
    # ارسال
    send_news(bot, db, news_fetcher, news_cache)
    
    logger.info("=" * 50)
    logger.info("✅ تمام شد")


if __name__ == "__main__":
    main()
