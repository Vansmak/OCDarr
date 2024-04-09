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
    # Sort series and return only the top 6
    active_series.sort(key=lambda series: series['dateAdded'], reverse=True)
    return active_series[:7]  # Return only the top 6 series

    
def fetch_sonarr_activity(preferences):
    activity_url = f"{preferences['sonarr_url']}/api/v3/history?page=1&pageSize=10&sortDir=desc"
    headers = {'X-Api-Key': preferences['sonarr_api_key']}
    response = requests.get(activity_url, headers=headers)
    if response.ok:
        activity_data = response.json().get('records', [])
        return activity_data
    return []
   
def fetch_upcoming_premieres(preferences):
    series_url = f"{preferences['sonarr_url']}/api/v3/series"
    headers = {'X-Api-Key': preferences['sonarr_api_key']}
    upcoming_premieres = []

    series_response = requests.get(series_url, headers=headers)
    if series_response.ok:
        series_list = series_response.json()
        for series in series_list:
            if 'nextAiring' in series:
                # Convert and format the next airing date
                next_airing_dt = datetime.fromisoformat(series['nextAiring'].replace('Z', '+00:00'))
                formatted_date = next_airing_dt.strftime('%Y-%m-%d at %H:%M')
                upcoming_premieres.append({
                    'name': series['title'],
                    'nextAiring': formatted_date,
                    'artwork_url': f"{preferences['sonarr_url']}/api/v3/mediacover/{series['id']}/banner.jpg?apikey={preferences['sonarr_api_key']}",
                    'sonarr_series_url': f"{preferences['sonarr_url']}/series/{series['titleSlug']}"
                })

    upcoming_premieres.sort(key=lambda x: x['nextAiring'])
    return upcoming_premieres