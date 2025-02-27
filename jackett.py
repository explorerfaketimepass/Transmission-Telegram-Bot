import requests
from prettytable import PrettyTable
import textwrap
from config import JACKETT_URL, JACKETT_TOKEN

def get_jackett_url():
    """Get Jackett URL from config."""
    return JACKETT_URL

def get_jackett_token():
    """Get Jackett API token from config."""
    token = JACKETT_TOKEN
    if not token:
        raise ValueError("JACKETT_TOKEN is not configured")
    return token

def human_readable_size(size, decimal_places=2):
    """Convert a size in bytes to a human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size < 1024.0 or unit == 'PB':
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"

def request_jackett(query):
    """Search for torrents using Jackett API."""
    print(f"Querying Jackett... {query}")
    token = get_jackett_token()
    
    params = {
        'apikey': token,
        'Query': query
    }
    url = f"{get_jackett_url()}/api/v2.0/indexers/all/results"
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        formatted_results, results = format_search_results(data)
        return (formatted_results, results)
    except requests.exceptions.RequestException as e:
        return (f"Error querying Jackett: {str(e)}", None)

def format_search_results(data):
    """Format Jackett search results into a pretty table."""
    results = data.get('Results', [])
    results = sorted(results, key=lambda x: x.get('Seeders', 0), reverse=True)
    
    table = PrettyTable(border=False, header=True, hrules=0, vrules=0, preserve_internal_border=False)
    table.field_names = ["No.", "Title", "Size", "Seeds"]
    
    # Filter out torrents larger than 121GB
    results = [torrent for torrent in results if torrent['Size'] <= 121474836480]
    
    for i, torrent in enumerate(results[:10]):
        title = "\n".join(textwrap.wrap(torrent['Title'], width=18))
        size = torrent['Size']
        size = human_readable_size(size) if size else 'Unknown' 
        seeders = torrent['Seeders']
        table.add_row([i+1, title, size, seeders])
    
    return str(table), results

def get_torrent_link(index, results):
    """Get the magnet link or direct link for a torrent."""
    if 0 <= index < len(results):
        torrent = results[index]
        return torrent.get('MagnetUri') or torrent.get('Link')
    else:
        raise IndexError("Invalid torrent index")
