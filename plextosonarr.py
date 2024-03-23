import json
import requests
import xml.etree.ElementTree as ET

# Load preferences from preferences.json
with open('preferences.json', 'r') as preferences_file:
    preferences = json.load(preferences_file)['preferences']

# Assign variables from preferences
PLEX_URL = preferences.get('plex_url') + '/status/sessions'
PLEX_TOKEN = preferences.get('plex_token')
SONARR_BASE_URL = preferences.get('sonarr_url') + '/api/v3'
SONARR_API_KEY = preferences.get('sonarr_api_key')
WATCHED_PERCENT = preferences.get('watched_percent', 90)
ALREADY_WATCHED_ACTION = preferences.get('already_watched', 'keep')

def get_plex_activity():
    response = requests.get(PLEX_URL, headers={'X-Plex-Token': PLEX_TOKEN})
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        for video in root.iter('Video'):
            if video.get('type') == 'episode':
                series_name = video.get('grandparentTitle')
                season_number = video.get('parentIndex')
                episode_number = video.get('index')
                return series_name, season_number, episode_number
    return None, None, None

def get_series_id(series_name):
    response = requests.get(f"{SONARR_BASE_URL}/series", headers={'X-Api-Key': SONARR_API_KEY})
    if response.status_code == 200:
        series_list = response.json()
        for series in series_list:
            if series['title'].lower() == series_name.lower():
                return series['id']
    return None

def get_episode_details(series_id, season_number):
    response = requests.get(f"{SONARR_BASE_URL}/episode?seriesId={series_id}&seasonNumber={season_number}", headers={'X-Api-Key': SONARR_API_KEY})
    if response.status_code == 200:
        return response.json()
    return []

def find_next_episode(episode_details, current_episode_number):
    episodes_after_current = [ep for ep in episode_details if ep['episodeNumber'] > int(current_episode_number)]
    return min(episodes_after_current, key=lambda x: x['episodeNumber']) if episodes_after_current else None

def trigger_episode_search_in_sonarr(episode_id):
    url = f"{SONARR_BASE_URL}/command"
    headers = {'X-Api-Key': SONARR_API_KEY, 'Content-Type': 'application/json'}
    data = {"name": "EpisodeSearch", "episodeIds": [episode_id]}
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 201:
        print("Episode search command sent to Sonarr successfully.")
    else:
        print("Failed to send episode search command to Sonarr.", response.text)

def monitor_episodes_in_sonarr(episode_ids):
    url = f"{SONARR_BASE_URL}/episode/monitor"
    headers = {'X-Api-Key': SONARR_API_KEY, 'Content-Type': 'application/json'}
    data = {"episodeIds": episode_ids, "monitored": True}
    response = requests.put(url, json=data, headers=headers)
    if response.ok:
        print(f"Episodes {episode_ids} set to monitored successfully.")
    else:
        print(f"Failed to set episodes {episode_ids} to monitored. Response: {response.text}")

def unmonitor_episode_in_sonarr(episode_id):
    url = f"{SONARR_BASE_URL}/episode/{episode_id}"
    headers = {'X-Api-Key': SONARR_API_KEY, 'Content-Type': 'application/json'}
    data = {"monitored": False}
    response = requests.put(url, json=data, headers=headers)
    if response.ok:
        print(f"Episode ID {episode_id} unmonitored successfully.")
    else:
        print(f"Failed to unmonitor episode ID {episode_id}. Response: {response.text}")

def find_episodes_to_delete(episode_details, current_episode_number):
    episodes_before_target = [ep for ep in episode_details if ep['episodeNumber'] < int(current_episode_number) - 1]
    return [ep['episodeFileId'] for ep in episodes_before_target if ep['episodeFileId'] > 0]

def delete_episodes_in_sonarr(episode_file_ids):
    for episode_file_id in episode_file_ids:
        url = f"{SONARR_BASE_URL}/episodeFile/{episode_file_id}"
        headers = {'X-Api-Key': SONARR_API_KEY}
        response = requests.delete(url, headers=headers)
        if response.ok:
            print(f"Successfully deleted episode file with ID: {episode_file_id}")
        else:
            print(f"Failed to delete episode file with ID: {episode_file_id}. Response: {response.text}")


def main():
    series_name, season_number, current_episode_number = get_plex_activity()
    if series_name and season_number and current_episode_number:
        series_id = get_series_id(series_name)
        if series_id:
            episode_details = get_episode_details(series_id, season_number)
            
            # Identify current, next, and episodes to delete
            current_episode = next((ep for ep in episode_details if ep['episodeNumber'] == int(current_episode_number)), None)
            next_episode = find_next_episode(episode_details, current_episode_number)
            episodes_to_delete_ids = find_episodes_to_delete(episode_details, current_episode_number)
            
            # Unmonitor current episode
            if current_episode and 'id' in current_episode:
                unmonitor_episode_in_sonarr(current_episode['id'])
            
            # Monitor and search next episode
            if next_episode and 'id' in next_episode:
                monitor_episodes_in_sonarr([next_episode['id']])
                if preferences['action_option'] in ['search', 'monitor']:
                    trigger_episode_search_in_sonarr(next_episode['id'])
            
            # Delete episodes as per preference
            if ALREADY_WATCHED_ACTION == "delete" and episodes_to_delete_ids:
                delete_episodes_in_sonarr(episodes_to_delete_ids)
            
            elif preferences['get_option'] == 'season':
                remaining_episodes = [ep for ep in episode_details if ep['episodeNumber'] > int(current_episode_number)]
                remaining_episode_ids = [ep['id'] for ep in remaining_episodes if 'id' in ep]
                if remaining_episode_ids:
                    monitor_episodes_in_sonarr(remaining_episode_ids)
                if ALREADY_WATCHED_ACTION == "delete" and episodes_to_delete_ids:
                    delete_episodes_in_sonarr(episodes_to_delete_ids)
    else:
        print("No active sessions found in Plex or unable to retrieve current activity.")

if __name__ == "__main__":
    main()
