import time
import json
from transmission_rpc import Client, TransmissionError
from config import (
    TRANSMISSION_HOST,
    TRANSMISSION_PORT,
    MAX_RETRIES,
    RETRY_DELAY,
    TORRENTS_FILE,
    TRANSMISSION_USERNAME,
    TRANSMISSION_PASSWORD,
    TRANSMISSION_PROTOCOL,
)


class TorrentManager:
    """Manager for interacting with Transmission torrent client."""

    def __init__(self):
        self.client = self._connect_to_transmission()
        self.torrents_dict = self._load_torrents_data()

    def _connect_to_transmission(self):
        """Connect to Transmission client with retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                client = Client(
                    host=TRANSMISSION_HOST,
                    port=TRANSMISSION_PORT,
                    username=TRANSMISSION_USERNAME,
                    password=TRANSMISSION_PASSWORD,
                    protocol=TRANSMISSION_PROTOCOL,
                )
                print("Connected to Transmission")
                return client
            except TransmissionError as e:
                if attempt < MAX_RETRIES - 1:
                    print(
                        f"Failed to connect to Transmission daemon. Retrying in {RETRY_DELAY} seconds..."
                    )
                    time.sleep(RETRY_DELAY)
                else:
                    raise e

    def _load_torrents_data(self):
        """Load torrent data from file."""
        try:
            with open(TORRENTS_FILE, "r") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_torrents_data(self):
        """Save torrent data to file."""
        with open(TORRENTS_FILE, "w") as file:
            json.dump(self.torrents_dict, file, indent=4)

    def add_torrent(self, torrent_link):
        """Add a torrent to Transmission."""
        try:
            torrent = self.client.add_torrent(torrent_link)
            return torrent
        except Exception as e:
            print(f"Error adding torrent: {e}")
            raise

    def get_torrent(self, torrent_id):
        """Get a torrent by ID."""
        return self.client.get_torrent(torrent_id)

    def get_all_torrents(self):
        """Get all torrents."""
        return self.client.get_torrents()

    def remove_torrent(self, torrent_id, delete_data=True):
        """Remove a torrent."""
        self.client.remove_torrent(ids=torrent_id, delete_data=delete_data)

    def start_torrent(self, torrent_id):
        """Start a torrent."""
        self.client.start_torrent(ids=torrent_id)

    def stop_torrent(self, torrent_id):
        """Stop a torrent."""
        self.client.stop_torrent(ids=torrent_id)

    def move_torrent_data(self, torrent_id, target_directory):
        """Move torrent data to a new directory."""
        self.client.move_torrent_data(torrent_id, target_directory)

    def get_free_space(self, directory):
        """Get free space in a directory."""
        return self.client.free_space(directory)
