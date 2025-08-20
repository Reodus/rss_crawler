# RSS Telegram Bot

A Telegram bot that aggregates and shares content from RSS feeds.

## Features

- Monitors multiple RSS feeds for new posts
- Automatically sends new posts to a Telegram channel
- Supports adding and listing RSS feeds through bot commands
- Cleans and formats post content for better readability
- Prevents duplicate posts
- Handles feed errors gracefully

## Setup

1. Clone this repository:
```bash
git clone <repository-url>
cd rss_crawler
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Create a Telegram bot and channel:
   - Talk to [@BotFather](https://t.me/botfather) on Telegram to create a new bot
   - Create a new channel and make your bot an administrator
   - Note down the bot token and channel ID

4. Create a `.env` file:
   - Copy `env.example` to `.env`
   - Fill in your bot token and channel ID

## Usage

1. Start the bot:
```bash
python bot.py
```

2. Bot Commands:
   - `/start` - Display welcome message and available commands
   - `/addfeed <url> <name>` - Add a new RSS feed
   - `/listfeeds` - List all configured feeds
   - `/removefeed <url>` - Remove an RSS feed
   - `/login <password>` - Log in to use the bot
   - `/logout` - Log out from the bot
   
## Contributing

Feel free to submit issues and enhancement requests!

## License

MIT License 