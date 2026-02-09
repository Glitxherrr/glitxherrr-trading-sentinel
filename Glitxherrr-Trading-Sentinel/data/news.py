import requests
import time
from datetime import datetime

# CryptoCompare free news feed
NEWS_URL = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"

# ---------------- Cache ----------------

_cached_news = []
_last_fetch = 0

# 30 minutes cooldown (matches UI refresh)
COOLDOWN = 1800  


# ---------------- Helpers ----------------

def _clean_text(text: str) -> str:
    if not text:
        return "Untitled"

    # Remove weird line breaks and spacing
    text = text.replace("\n", " ")
    text = " ".join(text.split())

    return text.strip()


def _safe_time(ts):
    try:
        return datetime.utcfromtimestamp(int(ts))
    except Exception:
        return None


# ---------------- Main Fetch ----------------

def fetch_important_news(limit: int = 8):
    """
    Returns list of dicts:
    {
        title: str
        source: str
        url: str
        published: datetime | None
    }
    """

    global _cached_news, _last_fetch

    now = time.time()

    # ---- Return cache if within cooldown ----
    if _cached_news and (now - _last_fetch) < COOLDOWN:
        return _cached_news[:limit]

    try:
        r = requests.get(NEWS_URL, timeout=10)
        r.raise_for_status()

        raw = r.json().get("Data", [])

        news = []

        for item in raw:

            title = _clean_text(item.get("title"))
            source = item.get("source", "Unknown")
            url = item.get("url")
            published = _safe_time(item.get("published_on"))

            news.append({
                "title": title,
                "source": source,
                "url": url,
                "published": published
            })

        # ---- Save cache ----
        _cached_news = news
        _last_fetch = now

        return news[:limit]

    except Exception:

        # Fallback to last known cache if API fails
        return _cached_news[:limit]
