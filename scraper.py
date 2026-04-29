import feedparser
from typing import List, Dict

def fetch_rss_news(feed_url: str, max_items: int = 10) -> List[Dict[str, str]]:
    """
    Fetches the latest news items from an RSS feed.
    """
    print(f"📡 Fetching RSS feed from: {feed_url}")
    feed = feedparser.parse(feed_url)
    
    if feed.bozo:
        print("❌ Error parsing the RSS feed.")
        return []

    news_items = []
    for entry in feed.entries[:max_items]:
        title = entry.get('title', '')
        # Description might contain HTML, we'll strip basic tags or let the LLM handle it
        summary = entry.get('summary', '') 
        link = entry.get('link', '')
        
        # Clean up very long summaries
        if len(summary) > 500:
            summary = summary[:500] + "..."
            
        news_items.append({
            "title": title,
            "summary": summary,
            "link": link
        })
        
    print(f"✅ Successfully fetched {len(news_items)} topics.")
    return news_items

if __name__ == "__main__":
    # Test the scraper
    techcrunch_rss = "https://techcrunch.com/feed/"
    news = fetch_rss_news(techcrunch_rss, max_items=2)
    for n in news:
        print(f"Title: {n['title']}\n")
