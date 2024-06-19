import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration settings from environment variables
SONARR_URL = os.getenv('SONARR_URL')
SONARR_API_KEY = os.getenv('SONARR_API_KEY')

def load_preferences():
    """
    Load preferences for Sonarr configuration.
    Returns a dictionary containing Sonarr URL and API key.
    """
    return {'SONARR_URL': SONARR_URL, 'SONARR_API_KEY': SONARR_API_KEY}

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
                    # Parse and make dateAdded offset-aware
                    date_added = datetime.fromisoformat(episode_file_details['dateAdded'].replace('Z', '+00:00'))
                    active_series.append({
                        'name': series['title'],
                        'latest_monitored_episode': f"S{episode['seasonNumber']}E{episode['episodeNumber']} - {episode['title']}",
                        'artwork_url': f"{SONARR_URL}/api/v3/mediacover/{series['id']}/poster.jpg?apikey={SONARR_API_KEY}",
                        'sonarr_series_url': f"{SONARR_URL}/series/{series['titleSlug']}",
                        'dateAdded': date_added
                    })
                    break  # Since we're only interested in the latest episode per series that meets the criteria

    # Sort series and return only the top 6
    active_series.sort(key=lambda series: series['dateAdded'], reverse=True)
    return active_series[:7]


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
