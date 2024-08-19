import os
import requests
import random
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image, ImageFilter
import io
import logging

# Load environment variables from .env file
load_dotenv()

# Configuration settings from environment variables
SONARR_URL = os.getenv('SONARR_URL')
SONARR_API_KEY = os.getenv('SONARR_API_KEY')
HA_WWW_PATH = '/app/backgrounds' 

# Setup logging
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_preferences():
    """
    Load preferences for Sonarr configuration.
    Returns a dictionary containing Sonarr URL and API key.
    """
    return {'SONARR_URL': SONARR_URL, 'SONARR_API_KEY': SONARR_API_KEY}

def fetch_random_fanart():
    """Fetch, blur, and save a random fanart from the Sonarr series list."""
    url = f"{SONARR_URL}/api/v3/series"
    headers = {'X-Api-Key': SONARR_API_KEY}
    try:
        response = requests.get(url, headers=headers)
        logger.info(f"Fetching series list from: {url}")
        
        if response.ok:
            series_list = response.json()
            random_series = random.choice(series_list)
            series_id = random_series['id']
            fanart_url = f"{SONARR_URL}/api/v3/mediacover/{series_id}/fanart.jpg?apikey={SONARR_API_KEY}"
            logger.info(f"Fetching fanart from: {fanart_url}")
            
            fanart_response = requests.get(fanart_url)
            if fanart_response.ok:
                # Open the image using PIL
                image = Image.open(io.BytesIO(fanart_response.content))
                
                # Resize the image to 3840x2160
                desired_width, desired_height = 3840, 2160
                resized_image = image.resize((desired_width, desired_height), Image.LANCZOS)

                # Apply the blur
                blurred_image = resized_image.filter(ImageFilter.GaussianBlur(radius=2))  # Adjust radius for more/less blur

                # Save the blurred image
                fanart_path = os.path.join(HA_WWW_PATH, "fanart.jpg")
                blurred_image.save(fanart_path, format='JPEG')
                logger.info(f"Saved blurred fanart as {fanart_path}")
            else:
                logger.error(f"Failed to fetch fanart. Status code: {fanart_response.status_code}, Content: {fanart_response.content[:100]}")
        else:
            logger.error(f"Failed to fetch series list. Status code: {response.status_code}, Content: {response.content[:100]}")
    except Exception as e:
        logger.error(f"Exception occurred while fetching or processing fanart: {str(e)}")

def get_series_list(preferences):
    url = f"{preferences['SONARR_URL']}/api/v3/series"
    headers = {'X-Api-Key': preferences['SONARR_API_KEY']}
    response = requests.get(url, headers=headers)
    if response.ok:
        series_list = response.json()
        # Sort the series list alphabetically by title
        sorted_series_list = sorted(series_list, key=lambda x: x['title'].lower())
        return sorted_series_list
    else:
        return []

def fetch_episode_file_details(episode_file_id):
    episode_file_url = f"{SONARR_URL}/api/v3/episodefile/{episode_file_id}"
    headers = {'X-Api-Key': SONARR_API_KEY}
    response = requests.get(episode_file_url, headers=headers)
    return response.json() if response.ok else None

def fetch_series_and_episodes(preferences):
    SONARR_URL = preferences['SONARR_URL']
    SONARR_API_KEY = preferences['SONARR_API_KEY']
    
    series_url = f"{SONARR_URL}/api/v3/series"
    headers = {'X-Api-Key': SONARR_API_KEY}
    active_series = []

    series_response = requests.get(series_url, headers=headers)
    series_list = series_response.json() if series_response.ok else []

    for series in series_list:
        episodes_url = f"{SONARR_URL}/api/v3/episode"
        params = {'seriesId': series['id']}
        episodes_response = requests.get(episodes_url, headers=headers, params=params)
        episodes = episodes_response.json() if episodes_response.ok else []

        for episode in episodes:
            if episode.get('monitored') and episode.get('hasFile'):
                episode_file_details = fetch_episode_file_details(episode['episodeFileId'])
                if episode_file_details and 'dateAdded' in episode_file_details:
                    date_added = datetime.fromisoformat(episode_file_details['dateAdded'].replace('Z', '+00:00'))
                    active_series.append({
                        'name': series['title'],
                        'latest_monitored_episode': f"S{episode['seasonNumber']}E{episode['episodeNumber']} - {episode['title']}",
                        'artwork_url': f"{SONARR_URL}/api/v3/mediacover/{series['id']}/poster.jpg?apikey={SONARR_API_KEY}",
                        'sonarr_series_url': f"{SONARR_URL}/series/{series['titleSlug']}",
                        'dateAdded': date_added,
                        'tag_id': 2 if 2 in series.get('tags', []) else None  # Check if tag_id 2 is in the tags list
                    })
                    break

    active_series.sort(key=lambda series: series['dateAdded'], reverse=True)
    return active_series[:12]

def fetch_upcoming_premieres(preferences):
    SONARR_URL = preferences['SONARR_URL']
    SONARR_API_KEY = preferences['SONARR_API_KEY']
    
    series_url = f"{SONARR_URL}/api/v3/series"
    headers = {'X-Api-Key': SONARR_API_KEY}
    upcoming_premieres = []

    series_response = requests.get(series_url, headers=headers)
    if series_response.ok:
        series_list = series_response.json()
        for series in series_list:
            if 'nextAiring' in series:
                next_airing_dt = datetime.fromisoformat(series['nextAiring'].replace('Z', '+00:00'))
                formatted_date = next_airing_dt.strftime('%Y-%m-%d at %H:%M')
                upcoming_premieres.append({
                    'name': series['title'],
                    'nextAiring': formatted_date,
                    'artwork_url': f"{SONARR_URL}/api/v3/mediacover/{series['id']}/poster.jpg?apikey={SONARR_API_KEY}",
                    'sonarr_series_url': f"{SONARR_URL}/series/{series['titleSlug']}"
                })

    upcoming_premieres.sort(key=lambda x: x['nextAiring'])
    return upcoming_premieres
