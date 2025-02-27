import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is required")

# Transmission configuration
TRANSMISSION_HOST = os.getenv("TRANSMISSION_HOST", "localhost")
TRANSMISSION_PORT = int(os.getenv("TRANSMISSION_PORT", 9091))
TRANSMISSION_PROTOCOL = os.getenv("TRANSMISSION_PROTOCOL", "http")
TRANSMISSION_USERNAME = os.getenv("TRANSMISSION_USERNAME")
TRANSMISSION_PASSWORD = os.getenv("TRANSMISSION_PASSWORD")


# Jackett configuration
JACKETT_URL = os.getenv("JACKETT_URL")
if not JACKETT_URL:
    raise ValueError("JACKETT_URL environment variable is required")

JACKETT_TOKEN = os.getenv("JACKETT_TOKEN")
if not JACKETT_TOKEN:
    raise ValueError("JACKETT_TOKEN environment variable is required")

# OMDB configuration
OMDB_TOKEN = os.getenv("OMDB_TOKEN")
if not OMDB_TOKEN:
    raise ValueError("OMDB_TOKEN environment variable is required")

# File paths
DATA_DIR = os.getenv("DATA_DIR", "/data")
MOVIES_DIR = os.getenv("MOVIES_DIR", f"{DATA_DIR}/completed/Movies")
TV_DIR = os.getenv("TV_DIR", f"{DATA_DIR}/completed/TV")

# Data storage files
TORRENTS_FILE = os.getenv("TORRENTS_FILE", "torrents_data.json")
USERS_FILE = os.getenv("USERS_FILE", "users_data.json")

# Retry settings for Transmission connection
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 30))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", 60))

# Authorized users (Telegram user IDs)
# None means all users are authorized
AUTHORIZED_USERS = [
    int(user_id)
    for user_id in os.getenv("AUTHORIZED_USERS", "").split(",")
    if user_id.strip()
] or None
