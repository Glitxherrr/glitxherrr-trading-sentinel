import feedparser
from datetime import datetime


GOLD_RSS = "https://www.investing.com/rss/news_11.rss"
MACRO_RSS = "https://www.investing.com/rss/news_14.rss"


def fetch_gold_news(limit=6):
    feeds = []

    for url in (GOLD_RSS, MACRO_RSS):
        feed = feedparser.parse(url)
        feeds.extend(feed.entries)

    out = []
    for e in feeds[:limit]:
        out.append({
            "title": e.title,
            "source": "Investing.com",
            "published": datetime(*e.published_parsed[:6]) if hasattr(e, "published_parsed") else None,
        })

    return out
