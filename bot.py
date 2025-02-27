from telegram.ext import Application, CommandHandler, MessageHandler
from telegram.ext.filters import REPLY
from commands import (
    search,
    handle_reply,
    imdb,
    add_torrent,
    list_torrents,
    delete_torrent,
    start_torrent,
    stop_torrent,
    move_to_movie,
    move_to_tv,
    help_command,
)
from config import TELEGRAM_TOKEN


def main():
    """Start the bot."""
    # Set up the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    # Search for torrents
    application.add_handler(CommandHandler("search", search))
    # Fetch IMDB link info and search for torrents
    application.add_handler(CommandHandler("imdb", imdb))
    # Add torrents using magnet links or torrent files
    application.add_handler(CommandHandler("torrent", add_torrent))
    # List torrents
    application.add_handler(CommandHandler("list", list_torrents))
    application.add_handler(CommandHandler("ls", list_torrents))
    # Start and stop torrents
    application.add_handler(CommandHandler("start", start_torrent))
    application.add_handler(CommandHandler("stop", stop_torrent))
    # Delete torrents
    application.add_handler(CommandHandler("delete", delete_torrent))
    # Handle replies to search results
    application.add_handler(MessageHandler(REPLY, handle_reply))
    # Move torrents to directories
    application.add_handler(CommandHandler("movie", move_to_movie))
    application.add_handler(CommandHandler("tv", move_to_tv))
    application.add_handler(CommandHandler("m", move_to_movie))
    application.add_handler(CommandHandler("t", move_to_tv))
    # Help command
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("h", help_command))

    # Run the bot
    application.run_polling()


if __name__ == "__main__":
    main()
