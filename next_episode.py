import requests
import xml.etree.ElementTree as ET

# Define the base URLs and API keys
PLEX_URL = 'plexurl:port/status/sessions'
PLEX_TOKEN = 'plextoken'
SONARR_BASE_URL = 'sonarrurl:port/api/v3'
SONARR_API_KEY = 'apikey'

def get_plex_activity():
    response = requests.get(PLEX_URL, headers={'X-Plex-Token': PLEX_TOKEN})
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        for video in root.iter('Video'):
            if video.get('type') == 'episode':
                series_name = video.get('grandparentTitle')
                episode_name = video.get('title').replace("'", "")  # Remove single quotes
                season_number = video.get('parentIndex')  # Extract season number
                return series_name, season_number, episode_name
    return None, None, None

def get_series_id(series_name):
    response = requests.get(f"{SONARR_BASE_URL}/series", headers={'X-Api-Key': SONARR_API_KEY})
    if response.status_code == 200:
        series_list = response.json()
        for series in series_list:
            if series['title'].lower() == series_name.lower():
                return series['id']
    return None

def get_next_episode(series_id, season_number, current_episode_name):
    response = requests.get(f"{SONARR_BASE_URL}/episode?seriesId={series_id}", headers={'X-Api-Key': SONARR_API_KEY})
    if response.status_code == 200:
        episode_list = response.json()
        next_episode = None
        found_current_episode = False
        for episode in episode_list:
            print(f"Comparing current episode: {current_episode_name} with episode: {episode['title']}")
            if episode['title'] in current_episode_name and episode['seasonNumber'] == int(season_number):
                found_current_episode = True
            elif found_current_episode and episode['seasonNumber'] == int(season_number):
                next_episode = episode
                break
        return next_episode
    return None

def trigger_episode_search_in_sonarr(episode_id):
    url = f"{SONARR_BASE_URL}/command"
    headers = {
        'X-Api-Key': SONARR_API_KEY,
        'Content-Type': 'application/json'
    }
    data = {
        "name": "EpisodeSearch",
        "episodeIds": [episode_id]
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 201:
        print("Download command sent to Sonarr successfully.")
    else:
        print("Failed to send download command to Sonarr.", response.text)

def main():
    series_name, season_number, current_episode_name = get_plex_activity()
    if series_name and season_number and current_episode_name:
        series_id = get_series_id(series_name)
        if series_id:
            print(f"Series found in Plex: {series_name}")
            print(f"Season: {season_number}")
            print(f"Current episode playing: {current_episode_name}")
            next_episode = get_next_episode(series_id, season_number, current_episode_name)
            if next_episode:
                print(f"Next episode after {current_episode_name}: {next_episode['title']}")
                # Trigger episode search in Sonarr for the next episode
                trigger_episode_search_in_sonarr(next_episode['id'])
            else:
                print("No next episode found.")
        else:
            print("Series ID not found in Sonarr.")
    else:
        print("No active sessions found in Plex.")

if __name__ == "__main__":
    main()
