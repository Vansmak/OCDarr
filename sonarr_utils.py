import json
import requests
from datetime import datetime

# Load configurations from preferences.json file
def load_preferences():
    with open('preferences.json', 'r') as file:
        return json.load(file)['preferences']

preferences = load_preferences()

def fetch_episode_file_details(episode_file_id, headers, sonarr_url):
    episode_file_url = f"{sonarr_url}/api/v3/episodefile/{episode_file_id}"
    response = requests.get(episode_file_url, headers=headers)
    return response.json() if response.ok else None

def fetch_series_and_episodes(preferences):
    series_url = f"{preferences['sonarr_url']}/api/v3/series"
    headers = {'X-Api-Key': preferences['sonarr_api_key']}
    active_series = []

    series_response = requests.get(series_url, headers=headers)
    series_list = series_response.json() if series_response.ok else []

    for series in series_list:
        episodes_url = f"{preferences['sonarr_url']}/api/v3/episode"
        params = {'seriesId': series['id']}
        episodes_response = requests.get(episodes_url, headers=headers, params=params)
        episodes = episodes_response.json() if episodes_response.ok else []

        for episode in episodes:
            if episode.get('monitored') and episode.get('hasFile'):
                episode_file_details = fetch_episode_file_details(episode['episodeFileId'], headers, preferences['sonarr_url'])
                if episode_file_details and 'dateAdded' in episode_file_details:
                    # Parse and make dateAdded offset-aware
                    date_added = datetime.fromisoformat(episode_file_details['dateAdded'].replace('Z', '+00:00'))
                    active_series.append({
                        'name': series['title'],
                        'latest_monitored_episode': f"S{episode['seasonNumber']}E{episode['episodeNumber']} - {episode['title']}",
                        'artwork_url': f"{preferences['sonarr_url']}/api/v3/mediacover/{series['id']}/banner.jpg?apikey={preferences['sonarr_api_key']}",
                        'sonarr_series_url': f"{preferences['sonarr_url']}/series/{series['titleSlug']}",
                        'dateAdded': date_added
                    })
                    break  # Since we're only interested in the latest episode per series that meets the criteria

    # Sort series by the most recently added episode
    active_series.sort(key=lambda series: series['dateAdded'], reverse=True)

    return active_series