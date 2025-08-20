import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.utils.markdown import hbold, hlink
import logging

from database import init_db, add_feed, get_all_feeds, update_feed_check_time, is_post_sent, mark_post_sent, remove_feed
from rss_crawler import RSSCrawler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get configuration from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
BOT_PASSWORD = os.getenv('BOT_PASSWORD')

if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, BOT_PASSWORD]):
    raise ValueError("Please set all required environment variables, including BOT_PASSWORD")

# Initialize bot and dispatcher
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
crawler = RSSCrawler()

# In-memory store for authenticated users (user_id: True)
authenticated_users = set()

# --- Authentication Decorator ---
def require_authentication(func):
    async def wrapper(message: types.Message, **kwargs):
        if message.from_user.id not in authenticated_users:
            await message.reply("🔒 This command requires you to be logged in. Please use /login <password>.")
            return
        return await func(message)
    return wrapper

# --- Command Handlers ---
@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    """This handler will be called when user sends `/start` command"""
    await message.reply(
        "👋 Hi! I'm a RSS Bot.\n\n"
        "Available commands:\n"
        "/login <password> - Log in to use the bot\n"
        "/logout - Log out from the bot\n"
        "/addfeed <url> <n> - Add a new RSS feed (requires login)\n"
        "/removefeed <url> - Remove an RSS feed (requires login)\n"
        "/listfeeds - List all configured feeds (requires login)"
    )

@dp.message(Command("login"))
async def login_command_handler(message: types.Message):
    """Handles the /login command."""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Please provide the password. Usage: /login <password>")
        return

    password_attempt = args[1]
    if password_attempt == BOT_PASSWORD:
        authenticated_users.add(message.from_user.id)
        await message.reply("✅ You are now logged in!")
    else:
        await message.reply("❌ Incorrect password.")

@dp.message(Command("logout"))
@require_authentication
async def logout_command_handler(message: types.Message):
    """Handles the /logout command."""
    if message.from_user.id in authenticated_users:
        authenticated_users.remove(message.from_user.id)
        await message.reply("✅ You have been logged out.")
    else:
        await message.reply("You are not currently logged in.")

@dp.message(Command("addfeed"))
@require_authentication
async def add_feed_command_handler(message: types.Message):
    """Add a new RSS feed."""
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply(
            "Please provide both URL and name for the feed.\n"
            "Usage: /addfeed <url> <name>"
        )
        return

    url = args[1]
    name = args[2]

    # Test if the feed is valid
    test_feed = await crawler.fetch_feed(url)
    if test_feed is None:
        await message.reply("❌ Invalid RSS feed URL or feed not accessible.")
        return

    await add_feed(url, name)
    await message.reply(f"✅ Successfully added feed: {name}")

@dp.message(Command("listfeeds"))
@require_authentication
async def list_feeds_handler(message: types.Message):
    """List all configured feeds."""
    feeds = await get_all_feeds()
    if not feeds:
        await message.reply("No feeds configured yet.")
        return

    response_message = "📚 Configured feeds:\n\n"
    for feed_item in feeds:
        response_message += f"• {feed_item['name']}: {feed_item['url']}\n"
    
    await message.reply(response_message)

@dp.message(Command("removefeed"))
@require_authentication
async def remove_feed_handler(message: types.Message):
    """Remove an RSS feed."""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply(
            "Please provide the URL of the feed to remove.\n"
            "Usage: /removefeed <url>"
        )
        return

    url = args[1]
    success = await remove_feed(url)
    
    if success:
        await message.reply(f"✅ Successfully removed feed: {url}")
    else:
        await message.reply("❌ Feed not found. Use /listfeeds to see available feeds.")

async def check_feeds_periodically():
    """Check all feeds for new posts and send them to the channel."""
    while True:
        try:
            feeds = await get_all_feeds()
            for feed_item in feeds:
                posts = await crawler.fetch_feed(feed_item['url'])
                if not posts:
                    continue

                for post in posts:
                    if not await is_post_sent(post['link']):
                        message_text = crawler.format_telegram_message(post, feed_item['name'])
                        
                        try:
                            await bot.send_message(
                                chat_id=TELEGRAM_CHANNEL_ID,
                                text=message_text,
                                parse_mode="HTML",
                                disable_web_page_preview=False
                            )
                            await mark_post_sent(feed_item['id'], post['link'])
                            await asyncio.sleep(2)  # Avoid hitting rate limits
                        except Exception as e:
                            logger.error(f"Error sending message: {str(e)}")

                await update_feed_check_time(feed_item['id'])
                
            await asyncio.sleep(900)  # Wait for 15 minutes before checking again
        except Exception as e:
            logger.error(f"Error in check_feeds_periodically: {str(e)}")
            await asyncio.sleep(60)  # Wait a minute before retrying

async def main():
    """Start the bot."""
    # Initialize the database
    await init_db()

    # Start the feed checker in the background
    asyncio.create_task(check_feeds_periodically())

    # Start polling
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")
