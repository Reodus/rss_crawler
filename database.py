import aiosqlite
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv('DATABASE_PATH', 'rss_feeds.db')

async def init_db():
    """Initialize the database with required tables."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS rss_feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                last_check TIMESTAMP
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS sent_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feed_id INTEGER,
                post_url TEXT UNIQUE NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (feed_id) REFERENCES rss_feeds (id)
            )
        ''')
        await db.commit()

async def add_feed(url: str, name: str):
    """Add a new RSS feed to the database."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            'INSERT OR IGNORE INTO rss_feeds (url, name) VALUES (?, ?)',
            (url, name)
        )
        await db.commit()

async def get_all_feeds():
    """Get all RSS feeds from the database."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM rss_feeds') as cursor:
            return await cursor.fetchall()

async def update_feed_check_time(feed_id: int):
    """Update the last check time for a feed."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            'UPDATE rss_feeds SET last_check = CURRENT_TIMESTAMP WHERE id = ?',
            (feed_id,)
        )
        await db.commit()

async def is_post_sent(post_url: str) -> bool:
    """Check if a post has already been sent."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            'SELECT 1 FROM sent_posts WHERE post_url = ?',
            (post_url,)
        ) as cursor:
            return await cursor.fetchone() is not None

async def mark_post_sent(feed_id: int, post_url: str):
    """Mark a post as sent."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            'INSERT INTO sent_posts (feed_id, post_url) VALUES (?, ?)',
            (feed_id, post_url)
        )
        await db.commit()

async def remove_feed(url: str) -> bool:
    """
    Remove an RSS feed from the database.
    
    Args:
        url (str): The URL of the feed to remove
        
    Returns:
        bool: True if the feed was removed, False if it didn't exist
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # First, get the feed_id
        async with db.execute(
            'SELECT id FROM rss_feeds WHERE url = ?',
            (url,)
        ) as cursor:
            feed = await cursor.fetchone()
            if not feed:
                return False
            
            feed_id = feed[0]
            
        # Remove related sent_posts first (due to foreign key constraint)
        await db.execute('DELETE FROM sent_posts WHERE feed_id = ?', (feed_id,))
        
        # Then remove the feed
        await db.execute('DELETE FROM rss_feeds WHERE id = ?', (feed_id,))
        await db.commit()
        return True 