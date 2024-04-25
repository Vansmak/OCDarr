import os
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration settings from environment variables
SONARR_URL = os.getenv('SONARR_URL')
SONARR_API_KEY = os.getenv('SONARR_API_KEY')
LOG_PATH = os.getenv('LOG_PATH', '/app/logs/app.log')
# Setup logging
logging.basicConfig(filename=LOG_PATH, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_preferences():
    """
    Load preferences for Sonarr configuration.
    Returns a dictionary containing Sonarr URL and API key.
    """
    return {'SONARR_URL': SONARR_URL, 'SONARR_API_KEY': SONARR_API_KEY}

def fetch_episode_file_details(episode_file_id, preferences):
    """
    Fetch details for a specific episode file by ID with timeout and error handling.
    """
    episode_file_url = f"{preferences['SONARR_URL']}/api/v3/episodefile/{episode_file_id}"
    headers = {'X-Api-Key': preferences['SONARR_API_KEY']}
    try:
        response = requests.get(episode_file_url, headers=headers, timeout=5)  # 5 seconds timeout
        response.raise_for_status()  # Raises stored HTTPError, if one occurred.
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch episode file details: {e}")
        return None

def fetch_series_and_episodes(preferences):
    """
    Fetch all series and their episodes with detailed error handling and timeout.
    """
    series_url = f"{preferences['SONARR_URL']}/api/v3/series"
    headers = {'X-Api-Key': preferences['SONARR_API_KEY']}
    active_series = []

    try:
        series_response = requests.get(series_url, headers=headers, timeout=5)  # 5 seconds timeout
        series_response.raise_for_status()
        series_list = series_response.json()

        for series in series_list:
            episodes_url = f"{preferences['SONARR_URL']}/api/v3/episode"
            params = {'seriesId': series['id']}
            episodes_response = requests.get(episodes_url, headers=headers, params=params, timeout=5)
            episodes_response.raise_for_status()
            episodes = episodes_response.json()

            for episode in episodes:
                if episode.get('monitored') and episode.get('hasFile'):
                    episode_file_details = fetch_episode_file_details(episode['episodeFileId'], preferences)
                    if episode_file_details and 'dateAdded' in episode_file_details:
                        date_added = datetime.fromisoformat(episode_file_details['dateAdded'].replace('Z', '+00:00'))
                        active_series.append({
                            'name': series['title'],
                            'latest_monitored_episode': f"S{episode['seasonNumber']}E{episode['episodeNumber']} - {episode['title']}",
                            'artwork_url': f"{preferences['SONARR_URL']}/api/v3/mediacover/{series['id']}/banner.jpg?apikey={preferences['SONARR_API_KEY']}",
                            'sonarr_series_url': f"{preferences['SONARR_URL']}/series/{series['titleSlug']}",
                            'dateAdded': date_added
                        })
    except requests.RequestException as e:
        logging.error(f"Failed to fetch series and episodes data: {e}")

    active_series.sort(key=lambda series: series['dateAdded'], reverse=True)
    return active_series[:7]

def fetch_upcoming_premieres(preferences):
    """
    Fetch upcoming premieres from Sonarr with timeout and detailed error handling.
    """
    series_url = f"{preferences['SONARR_URL']}/api/v3/series"
    headers = {'X-Api-Key': preferences['SONARR_API_KEY']}
    upcoming_premieres = []

    try:
        series_response = requests.get(series_url, headers=headers, timeout=5)  # 5 seconds timeout
        series_response.raise_for_status()  # Check for HTTP request errors
        series_list = series_response.json()

        for series in series_list:
            if 'nextAiring' in series:
                next_airing_dt = datetime.fromisoformat(series['nextAiring'].replace('Z', '+00:00'))
                formatted_date = next_airing_dt.strftime('%Y-%m-%d at %H:%M')
                upcoming_premieres.append({
                    'name': series['title'],
                    'nextAiring': formatted_date,
                    'artwork_url': f"{preferences['SONARR_URL']}/api/v3/mediacover/{series['id']}/banner.jpg?apikey={preferences['SONARR_API_KEY']}",
                    'sonarr_series_url': f"{preferences['SONARR_URL']}/series/{series['titleSlug']}"
                })
    except requests.RequestException as e:
        logging.error(f"Failed to fetch upcoming premieres: {e}")

    upcoming_premieres.sort(key=lambda x: x['nextAiring'])
    return upcoming_premieres


def fetch_tagged_series_names(preferences, tag_id=2):
    """
    Fetch series tagged with a specific ID from Sonarr, handling timeouts and errors.
    """
    series_url = f"{preferences['SONARR_URL']}/api/v3/series"
    headers = {'X-Api-Key': preferences['SONARR_API_KEY']}
    tagged_series = []

    try:
        series_response = requests.get(series_url, headers=headers, timeout=5)  # 5 seconds timeout
        series_response.raise_for_status()  # Check for HTTP request errors
        series_list = series_response.json()

        for series in series_list:
            if tag_id in series.get('tags', []):
                tagged_series.append({
                    'name': series['title'],
                    'id': series['id'],
                    'artwork_url': f"{preferences['SONARR_URL']}/api/v3/mediacover/{series['id']}/banner.jpg?apikey={preferences['SONARR_API_KEY']}",
                    'sonarr_series_url': f"{preferences['SONARR_URL']}/series/{series['titleSlug']}"
                })
    except requests.RequestException as e:
        logging.error(f"Failed to fetch tagged series: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while fetching tagged series: {e}")

    return tagged_series
