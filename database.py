import json
import os
from datetime import datetime
from typing import Any


class Database:
    """دیتابیس JSON"""
    
    def __init__(self, filename: str = "bot_database.json"):
        self.filename = filename
        self.data = self._load()
    
    def _load(self) -> dict:
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return self._default_data()
    
    def _default_data(self) -> dict:
        return {
            "stats": {
                "total_messages_sent": 0,
                "total_news_fetched": 0,
                "start_time": datetime.now().isoformat(),
                "last_run": None,
            },
            "logs": [],
        }
    
    def save(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"خطا در ذخیره: {e}")
    
    def increment_stat(self, key: str, value: int = 1):
        if "stats" not in self.data:
            self.data["stats"] = {}
        self.data["stats"][key] = self.data["stats"].get(key, 0) + value
        self.save()
    
    def get_stats(self) -> dict:
        return self.data.get("stats", {})
    
    def update_last_news_time(self):
        self.data["stats"]["last_run"] = datetime.now().isoformat()
        self.save()
    
    def add_log(self, message: str, level: str = "INFO"):
        if "logs" not in self.data:
            self.data["logs"] = []
        
        self.data["logs"].append({
            "time": datetime.now().isoformat(),
            "level": level,
            "message": message,
        })
        
        if len(self.data["logs"]) > 50:
            self.data["logs"] = self.data["logs"][-50:]
        
        self.save()
    
    def get_logs(self, count: int = 10) -> list:
        return self.data.get("logs", [])[-count:]
