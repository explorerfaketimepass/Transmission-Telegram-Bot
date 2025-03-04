import time
import requests
import traceback
from telegram import Update
from telegram.ext import CallbackContext
from telegram.error import BadRequest
from config import DATA_DIR, MOVIES_DIR, TV_DIR, AUTHORIZED_USERS
from torrent_manager import TorrentManager
from jackett import request_jackett, get_torrent_link
from imdb import get_imdb_info
from message_formatting import format_torrent_message, format_torrent_list

# Global variables
torrent_manager = TorrentManager()
torrent_messages = {}
torrent_last_progress = {}


# Authentication decorator
def authorized_only(func):
    """Decorator to check if user is authorized."""

    async def wrapper(update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        if not AUTHORIZED_USERS or user_id in AUTHORIZED_USERS:
            return await func(update, context)
        else:
            await update.message.reply_text("You are not authorized to use this bot.")

    return wrapper


# Torrent progress tracking
async def update_torrent_progress(chat_id, torrent_id, context: CallbackContext):
    """Update the progress of a specific torrent."""
    try:
        torrent = torrent_manager.get_torrent(torrent_id)
        progress = torrent.percent_done * 100

        # Check if progress has changed since last update
        if (
            torrent_id in torrent_last_progress
            and torrent_last_progress[torrent_id] == progress
        ):
            return  # Skip updating if progress hasn't changed

        message_text = format_torrent_message(
            torrent, torrent_manager.get_free_space(DATA_DIR)
        )

        if torrent_id in torrent_messages and chat_id in torrent_messages[torrent_id]:
            message_id = torrent_messages[torrent_id][chat_id]
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=message_text
            )
        else:
            sent_message = await context.bot.send_message(
                chat_id=chat_id, text=message_text
            )
            if torrent_id not in torrent_messages:
                torrent_messages[torrent_id] = {}
            torrent_messages[torrent_id][chat_id] = sent_message.message_id

        # Update the last known progress
        torrent_last_progress[torrent_id] = progress

        # Check if the torrent is complete
        if progress >= 100:
            # Remove the torrent from tracking
            if (
                torrent_id in torrent_messages
                and chat_id in torrent_messages[torrent_id]
            ):
                del torrent_messages[torrent_id][chat_id]
            if torrent_id in torrent_last_progress:
                del torrent_last_progress[torrent_id]
            # Stop the job
            jobs = context.job_queue.get_jobs_by_name(str(torrent_id))
            if jobs:
                jobs[0].schedule_removal()
            return
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass  # Ignore the error if the message content hasn't changed
        else:
            raise  # Re-raise the exception if it's not the specific "Message is not modified" error
    except Exception as e:
        print(f"Error updating torrent progress: {e}")
        if torrent_id in torrent_messages and chat_id in torrent_messages[torrent_id]:
            message_id = torrent_messages[torrent_id][chat_id]
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass
            del torrent_messages[torrent_id][chat_id]
        if torrent_id in torrent_last_progress:
            del torrent_last_progress[torrent_id]
        try:
            jobs = context.job_queue.get_jobs_by_name(str(torrent_id))
            if jobs:
                jobs[0].schedule_removal()
        except:
            pass


# Command handlers
@authorized_only
async def search(update: Update, context: CallbackContext):
    """Search for torrents using Jackett."""
    try:
        if len(context.args) > 0:
            query = " ".join(context.args)
            # Send the "Searching for torrents..." message
            search_message = await update.message.reply_text(
                f"Searching for torrents... {query}", parse_mode="HTML", quote=False
            )

            formatted_results, results = request_jackett(query)
            if not formatted_results:
                response_message = "`No results found.`"
            else:
                response_message = formatted_results
                response_message += "\n\nReply to this message with the index of the torrent you want to download."
                response_message = f"\n<pre>{response_message}</pre>"

            try:
                # Edit the message with the search results
                await search_message.edit_text(response_message, parse_mode="HTML")
            except BadRequest as e:
                print(f"Error editing message: {e}")
                await update.message.reply_text(
                    "An error occurred while formatting the message. Please try again later.",
                    quote=False,
                )

            context.chat_data["results"] = results  # Store results in chat data
        else:
            await update.message.reply_text("Usage: /search <query>")
    except Exception as e:
        print(f"An error occurred in search command: {e}")
        await update.message.reply_text("Something went wrong. Please try again later.")


@authorized_only
async def handle_reply(update: Update, context: CallbackContext):
    """Handle replies to search results."""
    user_reply = update.message.reply_to_message.text
    if not user_reply or "results" not in context.chat_data:
        await update.message.reply_text(
            "No search results found in context. Please start a new search.",
            quote=False,
        )
        return

    # Extracting the selected index from the reply
    try:
        index = int(update.message.text.split(".")[0]) - 1
        results = context.chat_data["results"]
        torrent_link = get_torrent_link(index, results)

        # Adding the torrent to Transmission
        try:
            if torrent_link.startswith("magnet:"):
                added_torrent = torrent_manager.add_torrent(torrent_link)
            else:
                # Handle non-magnet links
                try:
                    torrent_response = requests.get(torrent_link)
                    torrent_response.raise_for_status()
                    added_torrent = torrent_manager.add_torrent(torrent_link)
                except Exception as e:
                    # Try to extract magnet link from error
                    error_str = str(e)
                    if "magnet:?" in error_str:
                        magnet_link = (
                            "magnet:?" + error_str.split("magnet:?")[1].split(" ")[0]
                        )
                        added_torrent = torrent_manager.add_torrent(magnet_link)
                    else:
                        raise

            torrent_id = added_torrent.id
            chat_id = update.effective_chat.id
            torrent_name = added_torrent.name
            sent_message = await update.message.reply_text(
                f"Torrent added successfully to Transmission. - {torrent_name} (ID: {torrent_id})"
            )
            time.sleep(5)

            # Store the initial message ID
            if torrent_id not in torrent_messages:
                torrent_messages[torrent_id] = {}
            torrent_messages[torrent_id][chat_id] = sent_message.message_id

            # Start the repeating job
            context.job_queue.run_repeating(
                lambda c: update_torrent_progress(chat_id, torrent_id, c),
                interval=5,
                first=0,
                name=str(torrent_id),
            )
        except Exception as e:
            print(traceback.format_exc())
            await update.message.reply_text(f"Failed to add torrent: {str(e)}")
    except (IndexError, ValueError):
        await update.message.reply_text(
            "Invalid selection. Please reply with a valid index number.", quote=False
        )


async def check_torrents(context: CallbackContext):
    """
    Periodically check and update the progress of all active torrents.
    This function runs in the background and updates messages for ongoing downloads.
    """
    try:
        # Iterate through existing tracker messages
        for torrent_id, chat_dict in list(torrent_messages.items()):
            try:
                # Get the torrent details
                torrent = torrent_manager.get_torrent(torrent_id)
                progress = torrent.percent_done * 100

                # Get current free space once per torrent to ensure consistency
                free_space = torrent_manager.get_free_space(DATA_DIR)

                # Store previous progress to avoid unnecessary updates
                previous_progress = torrent_last_progress.get(torrent_id, -1)

                # Only update if progress has changed by at least 0.5%
                if abs(progress - previous_progress) < 0.5:
                    continue

                # Update the progress tracking
                torrent_last_progress[torrent_id] = progress

                # Update each chat's message for this torrent
                for chat_id, message_id in list(chat_dict.items()):
                    try:
                        # Generate updated message text
                        message_text = format_torrent_message(torrent, free_space)

                        # Update the message
                        try:
                            await context.bot.edit_message_text(
                                chat_id=chat_id,
                                message_id=message_id,
                                text=message_text,
                            )
                        except BadRequest as e:
                            # Ignore "message not modified" errors
                            if "Message is not modified" not in str(e):
                                raise

                        # Remove tracking if download is complete
                        if progress >= 100:
                            if (
                                torrent_id in torrent_messages
                                and chat_id in torrent_messages[torrent_id]
                            ):
                                del torrent_messages[torrent_id][chat_id]
                            if torrent_id in torrent_last_progress:
                                del torrent_last_progress[torrent_id]

                            # If no more chats are tracking this torrent, clean up
                            if not torrent_messages.get(torrent_id):
                                # Try to remove any per-torrent jobs
                                try:
                                    jobs = context.job_queue.get_jobs_by_name(
                                        str(torrent_id)
                                    )
                                    for job in jobs:
                                        job.schedule_removal()
                                except Exception as job_error:
                                    print(
                                        f"Error removing job for torrent {torrent_id}: {job_error}"
                                    )

                    except Exception as edit_error:
                        print(
                            f"Error updating message for torrent {torrent_id} in chat {chat_id}: {edit_error}"
                        )
                        # Clean up tracking if message update fails
                        if (
                            torrent_id in torrent_messages
                            and chat_id in torrent_messages[torrent_id]
                        ):
                            try:
                                # Try to delete the message if we can't update it
                                await context.bot.delete_message(
                                    chat_id=chat_id, message_id=message_id
                                )
                            except Exception:
                                pass  # Ignore errors when deleting
                            del torrent_messages[torrent_id][chat_id]

            except Exception as torrent_error:
                print(f"Error getting torrent {torrent_id}: {torrent_error}")
                # Remove tracking for this torrent if it can't be retrieved
                if torrent_id in torrent_messages:
                    del torrent_messages[torrent_id]
                if torrent_id in torrent_last_progress:
                    del torrent_last_progress[torrent_id]

    except Exception as global_error:
        print(f"Error in check_torrents: {global_error}")


@authorized_only
async def imdb(update: Update, context: CallbackContext):
    """Get movie info from IMDb and search for torrents."""
    if len(context.args) == 1:
        link = context.args[0]
        search_query = get_imdb_info(link)
        await update.message.reply_text(f"Searching for: {search_query}")

        formatted_results, results = request_jackett(search_query)
        if not formatted_results:
            response_message = "`No results found.`"
            await update.message.reply_text(
                response_message, parse_mode="MarkdownV2", quote=False
            )
        else:
            response_message = formatted_results
            response_message += "\n\nReply to this message with the index of the torrent you want to download."
            response_message = f"```\n{response_message}```"
            await update.message.reply_text(
                response_message, parse_mode="MarkdownV2", quote=False
            )
            context.chat_data["results"] = results  # Store results in chat data
    else:
        await update.message.reply_text("Usage: /imdb <movie url>")


@authorized_only
async def add_torrent(update: Update, context: CallbackContext):
    """Add a torrent using a magnet link or torrent URL."""
    if len(context.args) == 1:
        link = context.args[0]
        if link.startswith("magnet:") or link.endswith(".torrent"):
            try:
                added_torrent = torrent_manager.add_torrent(link)
                torrent_id = added_torrent.id
                chat_id = update.effective_chat.id
                sent_message = await update.message.reply_text(
                    "Torrent added successfully to Transmission."
                )

                # Store the initial message ID
                if torrent_id not in torrent_messages:
                    torrent_messages[torrent_id] = {}
                torrent_messages[torrent_id][chat_id] = sent_message.message_id

                # Start the repeating job
                context.job_queue.run_repeating(
                    lambda c: update_torrent_progress(chat_id, torrent_id, c),
                    interval=5,
                    first=0,
                    name=str(torrent_id),
                )
            except Exception as e:
                await update.message.reply_text(f"Failed to add torrent: {e}")
        else:
            await update.message.reply_text(
                "Please provide a valid magnet link or torrent file URL."
            )
    else:
        await update.message.reply_text("Usage: /torrent <magnet_link_or_torrent_url>")


@authorized_only
async def list_torrents(update: Update, context: CallbackContext):
    """List all torrents in the client."""
    torrents = torrent_manager.get_all_torrents()
    free_space = torrent_manager.get_free_space(DATA_DIR)

    # Get formatted messages
    messages = format_torrent_list(torrents, free_space)

    # Send each formatted message
    for message in messages:
        await update.message.reply_text(message, parse_mode="HTML", quote=False)


@authorized_only
async def delete_torrent(update: Update, context: CallbackContext):
    """Delete a torrent by ID."""
    if len(context.args) == 1:
        try:
            torrent_id = int(context.args[0])
            torrent = torrent_manager.get_torrent(torrent_id)
            torrent_manager.remove_torrent(torrent_id, delete_data=True)
            await update.message.reply_text(
                f"Torrent {torrent.name} deleted successfully."
            )
        except Exception as e:
            await update.message.reply_text(f"Failed to delete torrent: {e}")
    else:
        await update.message.reply_text("Usage: /delete <torrent_id>")


@authorized_only
async def start_torrent(update: Update, context: CallbackContext):
    """Start a paused torrent by ID."""
    if len(context.args) == 1:
        try:
            torrent_id = int(context.args[0])
            torrent = torrent_manager.get_torrent(torrent_id)
            torrent_manager.start_torrent(torrent_id)
            await update.message.reply_text(
                f"Torrent {torrent.name} started successfully."
            )
        except Exception as e:
            await update.message.reply_text(f"Failed to start torrent: {e}")
    else:
        await update.message.reply_text("Usage: /start <torrent_id>")


@authorized_only
async def stop_torrent(update: Update, context: CallbackContext):
    """Stop a torrent by ID."""
    if len(context.args) == 1:
        try:
            torrent_id = int(context.args[0])
            torrent = torrent_manager.get_torrent(torrent_id)
            torrent_manager.stop_torrent(torrent_id)
            await update.message.reply_text(
                f"Torrent {torrent.name} stopped successfully."
            )
        except Exception as e:
            await update.message.reply_text(f"Failed to stop torrent: {e}")
    else:
        await update.message.reply_text("Usage: /stop <torrent_id>")


@authorized_only
async def move_to_movie(update: Update, context: CallbackContext):
    """Move a torrent to the Movies directory."""
    if len(context.args) == 1:
        try:
            torrent_id = int(context.args[0])
            torrent = torrent_manager.get_torrent(torrent_id)
            torrent_manager.move_torrent_data(torrent_id, MOVIES_DIR)
            await update.message.reply_text(
                f"Torrent {torrent.name} moved to Movies directory."
            )
        except Exception as e:
            await update.message.reply_text(f"Failed to move torrent {torrent_id}: {e}")
    else:
        await update.message.reply_text("Usage: /movie <torrent_id> or /m <torrent_id>")


@authorized_only
async def move_to_tv(update: Update, context: CallbackContext):
    """Move a torrent to the TV directory."""
    if len(context.args) == 1:
        try:
            torrent_id = int(context.args[0])
            torrent = torrent_manager.get_torrent(torrent_id)
            torrent_manager.move_torrent_data(torrent_id, TV_DIR)
            await update.message.reply_text(
                f"Torrent {torrent.name} moved to TV directory."
            )
        except Exception as e:
            await update.message.reply_text(f"Failed to move torrent {torrent_id}: {e}")
    else:
        await update.message.reply_text("Usage: /tv <torrent_id> or /t <torrent_id>")


@authorized_only
async def help_command(update: Update, context: CallbackContext):
    """Show help message with available commands."""
    help_message = """
🌟 *Available Commands* 🌟

1️⃣ */list* - *Lists all torrents* with their IDs and percent-done status. It also shows the *free space*.
2️⃣ */delete <torrent_id>* - *Deletes a torrent* using its ID.
3️⃣ */start <torrent_id>* - *Starts a torrent* using its ID.
4️⃣ */stop <torrent_id>* - *Stops a torrent* using its ID.
5️⃣ */m <torrent_id>* - *Moves movie* to the *Movies* folder.
6️⃣ */t <torrent_id>* - *Moves TV series* to the *TV* folder.
7️⃣ */search <name>* - *Searches* for a movie or TV show (e.g., "The Matrix" or "Simpsons s01e01").
8️⃣ */imdb <link>* - *Fetches IMDb information* from a given IMDb link and searches it.
9️⃣ */torrent <magnet_link>* - *Adds a torrent* using a magnet link.
🔟 */ls* - *Same as* */list*.

💬 */help* - *Shows this help message*.
"""
    await update.message.reply_text(help_message, parse_mode="Markdown", quote=False)
