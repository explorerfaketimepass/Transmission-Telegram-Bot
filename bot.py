from telegram.ext import Application, CommandHandler, MessageHandler
from telegram.ext.filters import REPLY
from telegram import BotCommand
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
    check_torrents,
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
    ]
    await app.bot.set_my_commands(commands)


def main():
    """Start the bot."""
    # Set up the Application
    application = (
        Application.builder().token(TELEGRAM_TOKEN).post_init(set_commands).build()
    )

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

    # Update torrents

    # Run the bot
    application.run_polling()


if __name__ == "__main__":
    main()
