# 🚀 Transmission Telegram Bot

[![GitHub](https://img.shields.io/badge/GitHub-ExplorerFakeTimePass%2Ftransmission--telegram--bot-blue?logo=github)](https://github.com/explorerfaketimepass/transmission-telegram-bot)

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)](https://core.telegram.org/bots)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Transmission](https://img.shields.io/badge/Transmission-Client-blue)](https://transmissionbt.com/)
[![Transmission-RPC](https://img.shields.io/badge/Transmission--RPC-Client-blue)](https://github.com/trim21/transmission-rpc)
[![Jackett](https://img.shields.io/badge/Jackett-Server-blue)](https://github.com/Jackett/Jackett)
[![OMDb](https://img.shields.io/badge/OMDb-API-blue)](http://www.omdbapi.com/)
[![Docker](https://img.shields.io/badge/Docker-Container-blue?logo=docker)](https://www.docker.com/)

A powerful, feature-rich Telegram bot for searching, downloading, and managing torrents through Transmission. Search for content, get detailed information, monitor download progress, and manage your downloads - all from the convenience of Telegram.

## ✨ Features

- 🔍 **Search for torrents** using Jackett
- 🎬 **Fetch IMDb information** and use it to find torrents
- 📊 **Real-time download progress** with visual progress bars
- 📂 **Organized content management** with separate Movie and TV directories
- 🔒 **User authorization system** to control access to your torrent client
- 📱 **Beautiful formatting** for Telegram messages
- 🛠️ **Full torrent management** (add, start, stop, force start, delete)
- 📁 **File organization** with commands to move content to appropriate directories
- 📈 **Torrent statistics** including download speed, ETA, and size
- 💾 **Disk space monitoring** to prevent storage issues
- 🔄 **Robust connection handling** with automatic retry mechanisms

## 📋 Requirements

- Python 3.9 or higher
- Transmission daemon running and accessible
- Jackett server for torrent searching
- Telegram bot token (from [@BotFather](https://t.me/botfather))
- OMDb API key for IMDb lookups

## 🛠️ Installation

1. **Clone the repository**

```bash
git clone https://github.com/explorerfaketimepass/transmission-telegram-bot.git
cd transmission-telegram-bot
```

2. **Set up a virtual environment (recommended)**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

Create a `.env` file in the project root directory:

```
# Telegram configuration
TELEGRAM_TOKEN=your_telegram_bot_token

# Transmission configuration
# Default Transmission host is localhost
TRANSMISSION_HOST=localhost
# Default Transmission port is 9091
TRANSMISSION_PORT=9091
# If you are using HTTPS, set the following variable to 'https'
TRANSMISSION_PROTOCOL=http
# If you have authentication enabled, set the following two variables to your username and password
TRANSMISSION_USERNAME=admin
TRANSMISSION_PASSWORD=admin

# Jackett configuration
# Default Jackett URL is http://localhost:9117
JACKETT_URL=http://jackett.yourdomain.com
# Jackett API token
JACKETT_TOKEN=your_jackett_api_token

# OMDB configuration (for IMDb lookups)
OMDB_TOKEN=your_omdb_api_token

# File paths
# Default data directory is /data
DATA_DIR=/data
# Default Movies directory is /data/completed/Movies
MOVIES_DIR=/data/completed/Movies
# Default TV directory is /data/completed/TV
TV_DIR=/data/completed/TV

# Retry settings for Transmission connection
MAX_RETRIES=30
RETRY_DELAY=60

# Download Link Prefix
# This is the prefix that will be added to the download link
# This is useful if you are using a file indexer server like apache or nginx to serve the files
# If you are not using a file indexer server, leave this empty
DOWNLOAD_LINK_PREFIX=

# Security - comma separated list of Telegram user IDs who can use the bot
# Leave empty to allow all users
AUTHORIZED_USERS=123456789,987654321
```

## 🚀 Usage

### Start the bot

```bash
python bot.py
```

### Available Commands

| Command                                  | Description                                      |
| ---------------------------------------- | ------------------------------------------------ |
| `/search <query>` or `/s`                | Search for torrents matching your query          |
| `/imdb <link>`                           | Fetch IMDb information and search for the title  |
| `/torrent <link>` or `/magnet` or `/add` | Add a torrent using a magnet link or URL         |
| `/list` or `/ls`                         | List all torrents with progress                  |
| `/delete <id>` or `/del`                 | Delete a torrent and its data                    |
| `/start <id>`                            | Start a paused torrent                           |
| `/forcestart <id>` or `/fs`              | Force start a torrent (bypass queue)             |
| `/stop <id>`                             | Pause a torrent                                  |
| `/m <id>` or `/movie <id>`               | Move a completed torrent to the Movies directory |
| `/t <id>` or `/tv <id>`                  | Move a completed torrent to the TV directory     |
| `/info <id>` or `/i`                     | Get detailed information about a torrent         |
| `/help` or `/h`                          | Show help message                                |

## 🐳 Docker Setup

For easy deployment, you can use Docker:

```bash
# Build the Docker image
docker build -t torrentbot .

# Run the container
docker run -d --name torrentbot \
  --env-file .env \
  --network=host \
  torrentbot
```

## 📁 Project Structure

```
torrentbot/
├── bot.py               # Main entry point and bot initialization
├── commands.py          # Command handlers
├── config.py            # Configuration settings and environment vars
├── imdb.py              # IMDb API interaction
├── jackett.py           # Jackett API interaction
├── message_formatting.py # Telegram message formatting
├── torrent_manager.py   # Transmission client wrapper
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create this)
├── Dockerfile           # Docker configuration
├── .gitignore           # Git ignore patterns
└── README.md            # Project documentation
```

## ⚙️ Enhanced Features

### Real-time Progress Tracking

The bot automatically updates torrent progress messages in real-time, showing:

- Visual progress bars
- Download speed
- ETA (estimated time of arrival)
- File size
- Free disk space

### Content Organization

Once downloads are complete, easily organize your content:

- `/movie` command moves content to your Movies directory
- `/tv` command moves content to your TV Shows directory

### Concurrent Updates

The bot handles multiple commands simultaneously, making it responsive even when managing many torrents.

### Error Handling & Retry Logic

Robust error handling ensures the bot remains operational:

- Automatic reconnection to Transmission if connection is lost
- Graceful error messages for failed operations
- Background task execution to prevent UI blocking

## 🔒 Security Considerations

- Use the `AUTHORIZED_USERS` setting to restrict access to trusted users only
- Keep your API tokens secure and never commit them to version control
- Consider running Transmission with authentication
- For public deployments, use HTTPS for all API communications
- Docker provides an extra layer of isolation

## 🚫 Disclaimer

This tool is intended for downloading legal content only. Always respect copyright laws and the terms of service of the content providers.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.
