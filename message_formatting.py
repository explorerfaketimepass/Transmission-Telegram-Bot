from datetime import datetime
import pytz
import urllib.parse


def human_readable_size(size, decimal_places=2):
    """Convert a size in bytes to a human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if size < 1024.0 or unit == "PB":
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"


def format_date(date):
    """Convert UTC date to local timezone and format it."""
    local_timezone = pytz.timezone(
        "America/New_York"
    )  # Consider making this configurable
    local_date = date.replace(tzinfo=pytz.utc).astimezone(local_timezone)
    return local_date.strftime("%b %d %Y, %I:%M %p")


def format_torrent_message(torrent, free_space):
    """Format message for a torrent with a progress bar and limited name length."""
    # Truncate torrent name to 100 characters
    name = torrent.name[:100] + "..." if len(torrent.name) > 100 else torrent.name

    # Calculate progress and format size
    progress_percent = torrent.percent_done * 100
    progress_bar_length = 20
    filled_length = int(progress_bar_length * progress_percent // 100)
    bar = "█" * filled_length + "-" * (progress_bar_length - filled_length)
    readable_size = human_readable_size(torrent.total_size)
    readable_date = format_date(torrent.added_date)
    readable_free_space = human_readable_size(free_space)

    # URL encode the torrent name
    encoded_name = urllib.parse.quote(torrent.name)

    torrent_index_url = "http://index.harshalp.tech"

    # Format message based on download progress
    if torrent.percent_done < 1:
        return (
            f"ID: {torrent.id}, Name: {name}\n"
            f"Progress: [{bar}] {progress_percent:.2f}%\n"
            f"ETA: {torrent.eta}\nSize: {readable_size}"
            f"\nAdded: {readable_date}"
            f"\nFree Disk Space = {readable_free_space}"
        )
    else:
        return (
            f"ID: {torrent.id}, Name: {name}\n"
            f"Progress: [{bar}] {progress_percent:.2f}%\n"
            f"\nDownload link: {torrent_index_url}/{encoded_name}"
            f"\nFree Disk Space = {readable_free_space}"
        )


def format_torrent_list(torrents, free_space, chunk_size=10):
    """Format a list of torrents into message chunks for display."""
    if not torrents:
        return ["No torrents found."]
    
    # Group torrents into chunks
    torrent_chunks = [torrents[i:i+chunk_size] for i in range(0, len(torrents), chunk_size)]
    messages = []
    
    # Format each chunk as a separate message
    for i, chunk in enumerate(torrent_chunks):
        response_message = f"<b>Torrents ({i*chunk_size + 1}-{i*chunk_size + len(chunk)} of {len(torrents)}):</b>\n\n"
        
        # Add torrents to the message with nice formatting
        for torrent in chunk:
            progress_percent = torrent.percent_done * 100
            torrent_size = human_readable_size(torrent.total_size)
            
            response_message += f"<code>ID: {torrent.id}</code>\n"
            response_message += f"<b>{torrent.name}</b>\n"
            response_message += f"<code>Progress: {progress_percent:.2f}% | Size: {torrent_size}</code>\n\n"
        
        # Add free space information to the last message
        if i == len(torrent_chunks) - 1:
            response_message += f"<b>Free Space: {human_readable_size(free_space)}</b>"
        
        messages.append(response_message)
    
    return messages
