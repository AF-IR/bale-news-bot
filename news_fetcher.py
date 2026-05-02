import requests
import feedparser
import hashlib
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
import logging
import re

logger = logging.getLogger(__name__)


class NewsItem:
    """مدل یک خبر"""
    
    def __init__(self, title: str, link: str, summary: str = "", 
                 source: str = "", published: str = ""):
        self.title = title.strip()
        self.link = link.strip()
        self.summary = self._clean_summary(summary)
        self.source = source
        self.published = published
        self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        content = f"{self.title}{self.link}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _clean_summary(self, text: str) -> str:
        """پاکسازی و خلاصه‌سازی"""
        if not text:
            return ""
        
        # حذف HTML
        soup = BeautifulSoup(text, "lxml")
        text = soup.get_text(separator=" ")
        
        # حذف فاصله‌های اضافی
        text = re.sub(r'\s+', ' ', text).strip()
        
        # محدود به 250 کاراکتر
        if len(text) > 250:
            text = text[:247] + "..."
        
        return text
    
    def format_message(self, ad: str = "") -> str:
        """فرمت پیام خبر"""
        return f"""📰 <b>{self.title}</b>

{self.summary}

{ad}"""
    
    def __repr__(self):
        return f"<News: {self.title[:30]}>"


class NewsFetcher:
    """جمع‌آوری اخبار"""
    
    def __init__(self, feeds: List[dict], max_news: int = 15):
        self.feeds = feeds
        self.max_news = max_news
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; BaleNewsBot/1.0)",
            "Accept": "application/rss+xml, application/xml, text/xml",
        })
    
    def fetch_all(self) -> List[NewsItem]:
        """دریافت اخبار"""
        all_news = []
        
        for feed in self.feeds:
            try:
                news = self._fetch_rss(feed["url"], feed["name"])
                all_news.extend(news)
                logger.info(f"از {feed['name']}: {len(news)} خبر")
            except Exception as e:
                logger.error(f"خطا در {feed['name']}: {e}")
        
        # حذف تکراری بر اساس لینک
        seen = set()
        unique = []
        for item in all_news:
            if item.link not in seen:
                seen.add(item.link)
                unique.append(item)
        
        # مرتب‌سازی
        unique.sort(key=lambda x: x.published, reverse=True)
        return unique[:self.max_news]
    
    def _fetch_rss(self, url: str, source: str) -> List[NewsItem]:
        """دریافت از یک فید"""
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            items = []
            
            for entry in feed.entries[:self.max_news]:
                # خلاصه
                summary = ""
                for field in ['summary', 'description', 'content']:
                    if hasattr(entry, field):
                        summary = getattr(entry, field, "")
                        if summary:
                            break
                
                # تاریخ
                published = ""
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        from time import mktime
                        dt = datetime.fromtimestamp(mktime(entry.published_parsed))
                        published = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass
                
                news = NewsItem(
                    title=getattr(entry, 'title', 'بدون عنوان'),
                    link=getattr(entry, 'link', ''),
                    summary=summary,
                    source=source,
                    published=published,
                )
                items.append(news)
            
            return items
            
        except Exception as e:
            logger.error(f"خطا در {url}: {e}")
            return []


class NewsCache:
    """کش اخبار ارسال شده"""
    
    def __init__(self, db_file: str = "sent_news.json"):
        self.db_file = db_file
        self.sent_ids: set = set()
        self.sent_titles: set = set()  # بر اساس عنوان هم چک
        self._load()
    
    def _load(self):
        import json
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.sent_ids = set(data.get("sent_ids", []))
                self.sent_titles = set(data.get("sent_titles", []))
        except (FileNotFoundError, json.JSONDecodeError):
            self.sent_ids = set()
            self.sent_titles = set()
    
    def _save(self):
        import json
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "sent_ids": list(self.sent_ids),
                    "sent_titles": list(self.sent_titles),
                    "updated": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطا در ذخیره: {e}")
    
    def is_sent(self, news_id: str, title: str = "") -> bool:
        """چک تکراری بودن"""
        # چک با ID
        if news_id in self.sent_ids:
            return True
        
        # چک با عنوان (برای مواردی که لینک عوض شده)
        if title:
            # نرمال‌سازی عنوان
            normalized = self._normalize(title)
            for sent_title in self.sent_titles:
                if self._similar(normalized, sent_title):
                    return True
        
        return False
    
    def _normalize(self, text: str) -> str:
        """نرمال‌سازی متن برای مقایسه"""
        import re
        text = text.lower().strip()
        text = re.sub(r'[^\w\s\u0600-\u06FF]', '', text)  # فقط حروف و فارسی
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _similar(self, s1: str, s2: str) -> bool:
        """بررسی شباهت دو متن"""
        # اگر یکی زیرمجموعه دیگری باشد
        if len(s1) > 10 and len(s2) > 10:
            if s1 in s2 or s2 in s1:
                return True
            # چک کلمات مشترک
            words1 = set(s1.split())
            words2 = set(s2.split())
            if len(words1) > 3 and len(words2) > 3:
                common = words1 & words2
                if len(common) >= min(len(words1), len(words2)) * 0.7:
                    return True
        return False
    
    def mark_sent(self, news_id: str, title: str = ""):
        """علامت‌گذاری ارسال شده"""
        self.sent_ids.add(news_id)
        if title:
            self.sent_titles.add(self._normalize(title))
        
        # محدود به 500 خبر اخیر
        if len(self.sent_ids) > 500:
            self.sent_ids = set(list(self.sent_ids)[-500:])
        if len(self.sent_titles) > 500:
            self.sent_titles = set(list(self.sent_titles)[-500:])
        
        self._save()
    
    def clear(self):
        """پاک کردن کش"""
        self.sent_ids = set()
        self.sent_titles = set()
        self._save()
