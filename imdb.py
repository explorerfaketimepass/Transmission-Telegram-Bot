import aiohttp
from urllib.parse import urlparse, unquote
from config import OMDB_TOKEN


def get_omdb_token():
    """Get OMDB API token from config."""
    token = OMDB_TOKEN
    if not token:
        raise ValueError("OMDB_TOKEN is not configured")
    return token


def extract_imdb_id(imdb_url):
    """Extract IMDb ID from URL."""
    parsed_url = urlparse(imdb_url)
    path_parts = [part for part in parsed_url.path.split("/") if part]
    if path_parts:
        return unquote(path_parts[-1])
    else:
        raise ValueError("Couldn't find the IMDb ID from the URL")


async def get_imdb_info(imdb_url):
    """Get movie/show information from IMDb URL using OMDB API asynchronously."""
    try:
        imdb_id = extract_imdb_id(imdb_url)
        token = get_omdb_token()
        omdb_url = f"http://www.omdbapi.com/?apikey={token}&i={imdb_id}"

        async with aiohttp.ClientSession() as session:
            async with session.get(omdb_url) as response:
                response.raise_for_status()
                data = await response.json()

                if data.get("Response") == "True":
                    return f"{data.get('Title')} {data.get('Year')}"
                else:
                    return data.get("Error")

    except Exception as e:
        return str(e)
