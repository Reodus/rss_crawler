import feedparser
from datetime import datetime
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RSSCrawler:
    def __init__(self):
        self.feeds_cache = {}

    async def fetch_feed(self, url: str) -> Optional[List[Dict]]:
        """
        Fetch and parse an RSS feed.
        Returns a list of posts or None if there's an error.
        """
        try:
            # Try parsing with explicit encoding handlers
            feed = feedparser.parse(url, response_headers={'content-type': 'text/xml; charset=utf-8'})
            
            if feed.bozo and isinstance(feed.bozo_exception, UnicodeEncodeError):
                # If UTF-8 fails, try with ASCII
                feed = feedparser.parse(url, response_headers={'content-type': 'text/xml; charset=ascii'})
            
            if feed.bozo and not isinstance(feed.bozo_exception, UnicodeEncodeError):  # Only fail for non-encoding errors
                logger.error(f"Error parsing feed {url}: {feed.bozo_exception}")
                return None
            
            posts = []
            for entry in feed.entries:
                # Extract tags if they exist
                tags = []
                if 'tags' in entry:
                    tags.extend(tag.get('term', '') for tag in entry.tags)
                elif 'categories' in entry:
                    tags.extend(entry.categories)

                post = {
                    'title': entry.get('title', 'No title'),
                    'link': entry.get('link', ''),
                    'description': entry.get('description', ''),
                    'published': entry.get('published', datetime.now().isoformat()),
                    'tags': [tag for tag in tags if tag]  # Filter out empty tags
                }
                
                # Clean up the description (remove HTML tags if needed)
                if post['description']:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(post['description'], 'html.parser')
                    post['description'] = soup.get_text()[:500] + '...' if len(soup.get_text()) > 500 else soup.get_text()
                
                posts.append(post)
            
            return posts[:10]  # Return only the 10 most recent posts
            
        except Exception as e:
            logger.error(f"Error fetching feed {url}: {str(e)}")
            return None

    def format_telegram_message(self, post: Dict, feed_name: str) -> str:
        """Format a post for Telegram message."""

        # Escape HTML special characters
        title = post['title'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        link = post['link'].replace('"', '&quot;')  # Escape quotes in URL
        description = post['description'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        message = (
            f"{title}\n\n"
            f"<a href=\"{link}\">🔗 Link</a>\n\n"
            f"{description}\n\n"
            f"<i>Feed: {feed_name}</i>\n"
        )
        return message 