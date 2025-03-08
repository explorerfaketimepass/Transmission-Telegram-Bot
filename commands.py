import time
import asyncio
import traceback
from telegram import Update
from telegram.ext import CallbackContext
from telegram.error import BadRequest
from config import DATA_DIR, MOVIES_DIR, TV_DIR, AUTHORIZED_USERS
from torrent_manager import TorrentManager
from jackett import request_jackett, get_torrent_link, download_torrent_file
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
        torrent = await torrent_manager.get_torrent(torrent_id)
        progress = torrent.percent_done * 100

        # Check if progress has changed since last update
        if (
            torrent_id in torrent_last_progress
            and torrent_last_progress[torrent_id] == progress
        ):
            return  # Skip updating if progress hasn't changed

        free_space = await torrent_manager.get_free_space(DATA_DIR)
        message_text = format_torrent_message(torrent, free_space)

        if torrent_id in torrent_messages and chat_id in torrent_messages[torrent_id]:
            message_id = torrent_messages[torrent_id][chat_id]
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id, message_id=message_id, text=message_text
                )
            except BadRequest as e:
                if "Message is not modified" not in str(e):
                    raise
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

            formatted_results, results = await request_jackett(query)
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
                added_torrent = await torrent_manager.add_torrent(torrent_link)
            else:
                # Handle non-magnet links - download the torrent file first
                try:
                    torrent_data = await download_torrent_file(torrent_link)
                    added_torrent = await torrent_manager.add_torrent(torrent_data)
                except Exception as e:
                    # Try to extract magnet link from error
                    error_str = str(e)
                    if "magnet:?" in error_str:
                        magnet_link = (
                            "magnet:?" + error_str.split("magnet:?")[1].split(" ")[0]
                        )
                        added_torrent = await torrent_manager.add_torrent(magnet_link)
                    else:
                        raise

            torrent_id = added_torrent.id
            chat_id = update.effective_chat.id
            torrent_name = added_torrent.name
            sent_message = await update.message.reply_text(
                f"Torrent added successfully to Transmission. - {torrent_name} (ID: {torrent_id})"
            )

            await start_monitoring(context)

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


torrent_messages = {}  # Maps torrent_id -> {chat_id -> message_id}
torrent_last_progress = {}  # Maps torrent_id -> progress_percentage
monitoring_active = False  # Flag to track if monitoring is currently running


async def check_torrents(context: CallbackContext):
    """
    Periodically check and update the progress of all active torrents.
    """
    global monitoring_active

    try:
        # If no torrents are being tracked, stop the job
        if not torrent_messages:
            print("No torrents being tracked. Stopping monitoring job.")
            monitoring_active = False

            # Find and remove the check_torrents job
            jobs = context.job_queue.get_jobs_by_name("check_torrents")
            for job in jobs:
                job.schedule_removal()
            return

        # Iterate through existing tracker messages
        for torrent_id, chat_dict in list(torrent_messages.items()):
            try:
                # Get the torrent details
                torrent = await torrent_manager.get_torrent(torrent_id)
                progress = torrent.percent_done * 100

                # Get current free space once per torrent to ensure consistency
                free_space = await torrent_manager.get_free_space(DATA_DIR)

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
                            print(
                                f"Torrent {torrent_id} complete. Removing from tracking."
                            )
                            if chat_id in chat_dict:
                                del chat_dict[chat_id]

                            # If this chat_dict is now empty, remove the torrent entirely
                            if not chat_dict and torrent_id in torrent_messages:
                                del torrent_messages[torrent_id]

                            if torrent_id in torrent_last_progress:
                                del torrent_last_progress[torrent_id]

                    except Exception as edit_error:
                        print(
                            f"Error updating message for torrent {torrent_id} in chat {chat_id}: {edit_error}"
                        )
                        # Clean up tracking if message update fails
                        if chat_id in chat_dict:
                            try:
                                # Try to delete the message if we can't update it
                                await context.bot.delete_message(
                                    chat_id=chat_id, message_id=message_id
                                )
                            except Exception:
                                pass  # Ignore errors when deleting
                            del chat_dict[chat_id]

                        # If this chat_dict is now empty, remove the torrent entirely
                        if not chat_dict and torrent_id in torrent_messages:
                            del torrent_messages[torrent_id]

            except Exception as torrent_error:
                print(f"Error getting torrent {torrent_id}: {torrent_error}")
                # Remove tracking for this torrent if it can't be retrieved
                if torrent_id in torrent_messages:
                    del torrent_messages[torrent_id]
                if torrent_id in torrent_last_progress:
                    del torrent_last_progress[torrent_id]
                # Delete the message if it exists
                for chat_id, message_id in list(chat_dict.items()):
                    try:
                        await context.bot.delete_message(
                            chat_id=chat_id, message_id=message_id
                        )
                    except Exception:
                        pass

    except Exception as global_error:
        print(f"Error in check_torrents: {global_error}")
        # Don't stop monitoring due to a transient error


async def start_monitoring(context: CallbackContext):
    """Start the torrent monitoring if it's not already running."""
    global monitoring_active

    if not monitoring_active and torrent_messages:
        print("Starting torrent monitoring.")
        monitoring_active = True
        context.job_queue.run_repeating(
            check_torrents, interval=5, first=0, name="check_torrents"
        )


@authorized_only
async def imdb(update: Update, context: CallbackContext):
    """Get movie info from IMDb and search for torrents."""
    if len(context.args) == 1:
        link = context.args[0]
        search_query = await get_imdb_info(link)
        await update.message.reply_text(f"Searching for: {search_query}")

        formatted_results, results = await request_jackett(search_query)
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
                added_torrent = await torrent_manager.add_torrent(link)
                torrent_id = added_torrent.id
                chat_id = update.effective_chat.id

                # Send initial message
                sent_message = await update.message.reply_text(
                    "Torrent added successfully to Transmission."
                )

                # Give Transmission a moment to start processing
                await asyncio.sleep(1)

                # Get the torrent details and update the message
                torrent = await torrent_manager.get_torrent(torrent_id)
                free_space = await torrent_manager.get_free_space(DATA_DIR)
                message_text = format_torrent_message(torrent, free_space)

                try:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=sent_message.message_id,
                        text=message_text,
                    )
                except Exception:
                    # If can't edit, send a new message
                    sent_message = await update.message.reply_text(message_text)

                # Store the message ID for tracking
                if torrent_id not in torrent_messages:
                    torrent_messages[torrent_id] = {}
                torrent_messages[torrent_id][chat_id] = sent_message.message_id

                # Set initial progress tracking
                torrent_last_progress[torrent_id] = torrent.percent_done * 100

                # Start monitoring if not already running
                await start_monitoring(context)

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
    torrents = await torrent_manager.get_all_torrents()
    free_space = await torrent_manager.get_free_space(DATA_DIR)

    # Get formatted messages
    messages = format_torrent_list(torrents, free_space)

    # Send each formatted message
    for message in messages:
        await update.message.reply_text(message, parse_mode="HTML", quote=False)


@authorized_only
async def delete_torrent(update: Update, context: CallbackContext):
    """Delete one or multiple torrents by ID(s)."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /delete <torrent_id> [torrent_id2 torrent_id3 ...]"
        )
        return

    success_count = 0
    failed_count = 0
    success_names = []

    for arg in context.args:
        try:
            torrent_id = int(arg)
            torrent = await torrent_manager.get_torrent(torrent_id)
            await torrent_manager.remove_torrent(torrent_id, delete_data=True)
            success_count += 1
            success_names.append(f"{torrent.name} (ID: {torrent_id})")

            # Clean up tracking data if the torrent was being monitored
            if torrent_id in torrent_messages:
                del torrent_messages[torrent_id]
            if torrent_id in torrent_last_progress:
                del torrent_last_progress[torrent_id]

        except Exception as e:
            failed_count += 1
            await update.message.reply_text(f"Failed to delete torrent {arg}: {e}")

    # Report results
    if success_count > 0:
        names_text = "\n- ".join(success_names)
        await update.message.reply_text(
            f"Successfully deleted {success_count} torrent{'s' if success_count > 1 else ''}:\n- {names_text}"
        )

    if failed_count == 0 and success_count == 0:
        await update.message.reply_text("No valid torrent IDs provided.")


@authorized_only
async def start_torrent(update: Update, context: CallbackContext):
    """Start one or multiple paused torrents by ID."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /start <torrent_id> [torrent_id2 torrent_id3 ...]"
        )
        return

    success_count = 0
    failed_count = 0
    success_names = []

    for arg in context.args:
        try:
            torrent_id = int(arg)
            torrent = await torrent_manager.get_torrent(torrent_id)
            await torrent_manager.start_torrent(torrent_id)
            success_count += 1
            success_names.append(f"{torrent.name} (ID: {torrent_id})")
        except Exception as e:
            failed_count += 1
            await update.message.reply_text(f"Failed to start torrent {arg}: {e}")

    # Report results
    if success_count > 0:
        if success_count == 1:
            await update.message.reply_text(
                f"Torrent {success_names[0]} started successfully."
            )
        else:
            names_text = "\n- ".join(success_names)
            await update.message.reply_text(
                f"Successfully started {success_count} torrents:\n- {names_text}"
            )

    if failed_count == 0 and success_count == 0:
        await update.message.reply_text("No valid torrent IDs provided.")


@authorized_only
async def force_start_torrent(update: Update, context: CallbackContext):
    """Force start one or multiple torrents by ID."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /force_start <torrent_id> [torrent_id2 torrent_id3 ...]"
        )
        return

    success_count = 0
    failed_count = 0
    success_names = []

    for arg in context.args:
        try:
            torrent_id = int(arg)
            torrent = await torrent_manager.get_torrent(torrent_id)
            await torrent_manager.force_start_torrent(torrent_id)
            success_count += 1
            success_names.append(f"{torrent.name} (ID: {torrent_id})")
        except Exception as e:
            failed_count += 1
            await update.message.reply_text(f"Failed to force start torrent {arg}: {e}")

    # Report results
    if success_count > 0:
        if success_count == 1:
            await update.message.reply_text(
                f"Torrent {success_names[0]} force started successfully."
            )
        else:
            names_text = "\n- ".join(success_names)
            await update.message.reply_text(
                f"Successfully force started {success_count} torrents:\n- {names_text}"
            )

    if failed_count == 0 and success_count == 0:
        await update.message.reply_text("No valid torrent IDs provided.")


@authorized_only
async def stop_torrent(update: Update, context: CallbackContext):
    """Stop one or multiple torrents by ID."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /stop <torrent_id> [torrent_id2 torrent_id3 ...]"
        )
        return

    success_count = 0
    failed_count = 0
    success_names = []

    for arg in context.args:
        try:
            torrent_id = int(arg)
            torrent = await torrent_manager.get_torrent(torrent_id)
            await torrent_manager.stop_torrent(torrent_id)
            success_count += 1
            success_names.append(f"{torrent.name} (ID: {torrent_id})")
        except Exception as e:
            failed_count += 1
            await update.message.reply_text(f"Failed to stop torrent {arg}: {e}")

    # Report results
    if success_count > 0:
        if success_count == 1:
            await update.message.reply_text(
                f"Torrent {success_names[0]} stopped successfully."
            )
        else:
            names_text = "\n- ".join(success_names)
            await update.message.reply_text(
                f"Successfully stopped {success_count} torrents:\n- {names_text}"
            )

    if failed_count == 0 and success_count == 0:
        await update.message.reply_text("No valid torrent IDs provided.")


@authorized_only
async def move_to_movie(update: Update, context: CallbackContext):
    """Move a torrent to the Movies directory."""
    if len(context.args) == 1:
        try:
            torrent_id = int(context.args[0])
            torrent = await torrent_manager.get_torrent(torrent_id)
            await torrent_manager.move_torrent_data(torrent_id, MOVIES_DIR)
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
            torrent = await torrent_manager.get_torrent(torrent_id)
            await torrent_manager.move_torrent_data(torrent_id, TV_DIR)
            await update.message.reply_text(
                f"Torrent {torrent.name} moved to TV directory."
            )
        except Exception as e:
            await update.message.reply_text(f"Failed to move torrent {torrent_id}: {e}")
    else:
        await update.message.reply_text("Usage: /tv <torrent_id> or /t <torrent_id>")


@authorized_only
async def info_torrent(update: Update, context: CallbackContext):
    """Get info about a specific torrent and start monitoring its progress."""
    if len(context.args) == 1:
        try:
            torrent_id = int(context.args[0])
            torrent = await torrent_manager.get_torrent(torrent_id)
            chat_id = update.effective_chat.id

            # Get initial details
            free_space = await torrent_manager.get_free_space(DATA_DIR)
            message_text = format_torrent_message(torrent, free_space)

            # Send initial message
            sent_message = await update.message.reply_text(
                message_text, parse_mode="HTML", quote=False
            )

            # Store the message ID for tracking
            if torrent_id not in torrent_messages:
                torrent_messages[torrent_id] = {}
            torrent_messages[torrent_id][chat_id] = sent_message.message_id

            # Set initial progress tracking
            torrent_last_progress[torrent_id] = torrent.percent_done * 100

            # Start monitoring if not already running
            await start_monitoring(context)

        except Exception as e:
            await update.message.reply_text(f"Failed to get torrent info: {e}")
    else:
        await update.message.reply_text("Usage: /info <torrent_id>")


@authorized_only
async def help_command(update: Update, context: CallbackContext):
    """Show help message with available commands."""
    help_message = """
🌟 *Available Commands* 🌟

1. */list* or */ls* - *Lists all torrents* with their IDs and progress.
2. */delete or /del <torrent_id> - *Deletes* one or more torrents.
3. */start <torrent_id>* - *Starts* a paused torrent.
4. */force_start or /fs <torrent_id>* - *Force starts* a torrent.
5. */stop <torrent_id>* - *Stops* a torrent.
6. */m <torrent_id>* or */movie <id>* - *Move* to *Movies* folder.
7. */t <torrent_id>* or */tv <id>* - *Move* to *TV* folder.
8. */search or /s <query>* - *Search* for content (e.g., "The Matrix", "Simpsons s01e01").
9. */imdb <link>* - Search using *IMDb information*.
10. */torrent or /magnet or /add <magnet_link>* - *Add* a torrent via magnet link.
11. */info or /i <torrent_id>* - Get *detailed info* about a torrent.

💬 */help or /h* - *Shows this help message*.
"""
    await update.message.reply_text(help_message, parse_mode="Markdown", quote=False)
