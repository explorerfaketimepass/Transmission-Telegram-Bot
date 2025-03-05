import time
import aiohttp
import asyncio
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
from transmission_rpc import Client, TransmissionError
from config import (
    TRANSMISSION_HOST,
    TRANSMISSION_PORT,
    MAX_RETRIES,
    RETRY_DELAY,
    TRANSMISSION_USERNAME,
    TRANSMISSION_PASSWORD,
    TRANSMISSION_PROTOCOL,
)

# Thread pool for executing blocking operations
executor = ThreadPoolExecutor(max_workers=10)


def run_in_executor(func):
    """Decorator to run a synchronous function in a thread pool executor."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, lambda: func(*args, **kwargs))

    return wrapper


class TorrentManager:
    """Manager for interacting with Transmission torrent client."""

    def __init__(self):
        self.client = None
        self.lock = asyncio.Lock()

    async def ensure_connected(self):
        """Ensure connection to Transmission client exists."""
        async with self.lock:
            if self.client is None:
                self.client = await self._connect_to_transmission()
            return self.client

    async def _connect_to_transmission(self):
        """Connect to Transmission client with retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                # This is synchronous, running it in a thread
                client = await self._create_client()
                print("Connected to Transmission")
                return client
            except TransmissionError as e:
                if attempt < MAX_RETRIES - 1:
                    print(
                        f"Failed to connect to Transmission daemon. Retrying in {RETRY_DELAY} seconds..."
                    )
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    raise e

    @run_in_executor
    def _create_client(self):
        """Create Transmission client (runs in thread pool)."""
        return Client(
            host=TRANSMISSION_HOST,
            port=TRANSMISSION_PORT,
            username=TRANSMISSION_USERNAME,
            password=TRANSMISSION_PASSWORD,
            protocol=TRANSMISSION_PROTOCOL,
        )

    async def add_torrent(self, torrent_link):
        """Add a torrent to Transmission."""
        try:
            client = await self.ensure_connected()
            return await self._add_torrent_sync(client, torrent_link)
        except Exception as e:
            print(f"Error adding torrent: {e}")
            raise

    @run_in_executor
    def _add_torrent_sync(self, client, torrent_link):
        """Add torrent synchronously (runs in thread pool)."""
        return client.add_torrent(torrent_link)

    async def get_torrent(self, torrent_id):
        """Get a torrent by ID."""
        client = await self.ensure_connected()
        return await self._get_torrent_sync(client, torrent_id)

    @run_in_executor
    def _get_torrent_sync(self, client, torrent_id):
        """Get torrent synchronously (runs in thread pool)."""
        return client.get_torrent(torrent_id)

    async def get_all_torrents(self):
        """Get all torrents."""
        client = await self.ensure_connected()
        return await self._get_all_torrents_sync(client)

    @run_in_executor
    def _get_all_torrents_sync(self, client):
        """Get all torrents synchronously (runs in thread pool)."""
        return client.get_torrents()

    async def remove_torrent(self, torrent_id, delete_data=True):
        """Remove a torrent."""
        client = await self.ensure_connected()
        await self._remove_torrent_sync(client, torrent_id, delete_data)

    @run_in_executor
    def _remove_torrent_sync(self, client, torrent_id, delete_data):
        """Remove torrent synchronously (runs in thread pool)."""
        client.remove_torrent(ids=torrent_id, delete_data=delete_data)

    async def start_torrent(self, torrent_id):
        """Start a torrent."""
        client = await self.ensure_connected()
        await self._start_torrent_sync(client, torrent_id)

    @run_in_executor
    def _start_torrent_sync(self, client, torrent_id):
        """Start torrent synchronously (runs in thread pool)."""
        client.start_torrent(ids=torrent_id)

    async def stop_torrent(self, torrent_id):
        """Stop a torrent."""
        client = await self.ensure_connected()
        await self._stop_torrent_sync(client, torrent_id)

    @run_in_executor
    def _stop_torrent_sync(self, client, torrent_id):
        """Stop torrent synchronously (runs in thread pool)."""
        client.stop_torrent(ids=torrent_id)

    async def move_torrent_data(self, torrent_id, target_directory):
        """Move torrent data to a new directory."""
        client = await self.ensure_connected()
        await self._move_torrent_data_sync(client, torrent_id, target_directory)

    @run_in_executor
    def _move_torrent_data_sync(self, client, torrent_id, target_directory):
        """Move torrent data synchronously (runs in thread pool)."""
        client.move_torrent_data(torrent_id, target_directory)

    async def get_free_space(self, directory):
        """Get free space in a directory."""
        client = await self.ensure_connected()
        return await self._get_free_space_sync(client, directory)

    @run_in_executor
    def _get_free_space_sync(self, client, directory):
        """Get free space synchronously (runs in thread pool)."""
        return client.free_space(directory)

    # force start torrent
    async def force_start_torrent(self, torrent_id):
        """Force start a torrent."""
        client = await self.ensure_connected()
        await self._force_start_torrent_sync(client, torrent_id)

    @run_in_executor
    def _force_start_torrent_sync(self, client, torrent_id):
        """Force start torrent synchronously (runs in thread pool)."""
        client.start_torrent(ids=torrent_id, bypass_queue=True)
