from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.ext import JobQueue
from telegram import BotCommand
from commands import (
    search,
    handle_reply,
    imdb,
    add_torrent,
    list_torrents,
    delete_torrent,
    start_torrent,
    force_start_torrent,
    stop_torrent,
    move_to_movie,
    move_to_tv,
    help_command,
    torrent_manager,
    info_torrent,
)
from config import TELEGRAM_TOKEN


async def set_commands(app: Application):
    """Set the bot commands."""
    commands = [
        BotCommand(
            command="list",
            description="Lists all the torrents with their ids and percent done status. It also shows the free space.",
        ),
        BotCommand(command="delete", description="Deletes a torrent using its id."),
        BotCommand(command="start", description="Starts a torrent using its id."),
        BotCommand(command="stop", description="Stops a torrent using its id."),
        BotCommand(command="movie", description="Move Movie to Movies folder"),
        BotCommand(command="tv", description="Move TV Series to TV folder"),
        BotCommand(
            command="search",
            description="Search for a movie or TV show (e.g., 'The Matrix' or 'Simpsons s01e01')",
        ),
        BotCommand(
            command="imdb",
            description="Get information from an IMDb link and search it",
        ),
        BotCommand(command="torrent", description="Add a torrent using a magnet link."),
        BotCommand(command="ls", description="Same as /list"),
        BotCommand(command="h", description="To see all commands"),
        BotCommand(command="info", description="Get information about a torrent"),
        BotCommand(
            command="forcestart", description="Force start a torrent using its id."
        ),
        BotCommand(command="fs", description="Same as /forcestart"),
    ]
    await app.bot.set_my_commands(commands)


async def post_init(app: Application):
    """Run post-initialization tasks."""
    # Set up bot commands
    await set_commands(app)

    # Initialize the torrent manager
    try:
        # Establish connection to Transmission before accepting commands
        await torrent_manager.ensure_connected()
    except Exception as e:
        print(f"Error initializing torrent manager: {e}")
        # We'll let the application continue, and retry connections later


def main():
    """Start the bot."""
    # Set up the Application with concurrency settings, proper timeouts, and job queue
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .concurrent_updates(True)  # Enable concurrent updates
        .connection_pool_size(16)  # Increase connection pool size
        .get_updates_read_timeout(30.0)
        .get_updates_write_timeout(30.0)
        .get_updates_connect_timeout(30.0)
        .job_queue(JobQueue())
        .build()
    )

    # Add handlers
    # Search for torrents
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("s", search))
    # Fetch IMDB link info and search for torrents
    application.add_handler(CommandHandler("imdb", imdb))
    # Add torrents using magnet links or torrent files
    application.add_handler(CommandHandler("torrent", add_torrent))
    application.add_handler(CommandHandler("magnet", add_torrent))
    application.add_handler(CommandHandler("add", add_torrent))
    # List torrents
    application.add_handler(CommandHandler("list", list_torrents))
    application.add_handler(CommandHandler("ls", list_torrents))
    # Start and stop torrents
    application.add_handler(CommandHandler("start", start_torrent))
    application.add_handler(CommandHandler("stop", stop_torrent))
    application.add_handler(CommandHandler("forcestart", force_start_torrent))
    application.add_handler(CommandHandler("fs", force_start_torrent))
    # Delete torrents
    application.add_handler(CommandHandler("delete", delete_torrent))
    application.add_handler(CommandHandler("del", delete_torrent))
    # Handle replies to search results
    application.add_handler(MessageHandler(filters.REPLY, handle_reply))
    # Move torrents to directories
    application.add_handler(CommandHandler("movie", move_to_movie))
    application.add_handler(CommandHandler("tv", move_to_tv))
    application.add_handler(CommandHandler("m", move_to_movie))
    application.add_handler(CommandHandler("t", move_to_tv))
    # Help command
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("h", help_command))
    # Torrent info command
    application.add_handler(CommandHandler("info", info_torrent))
    application.add_handler(CommandHandler("i", info_torrent))

    # Add error handler
    application.add_error_handler(error_handler)

    # Run the bot with polling
    application.run_polling(allowed_updates=["message", "callback_query"])


async def error_handler(update, context):
    """Handle errors."""
    print(f"An error occurred: {context.error}")
    # Log the error before we do anything else
    print(f"Update {update} caused error {context.error}")


if __name__ == "__main__":
    main()
