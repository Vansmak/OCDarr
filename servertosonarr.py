import os
import requests
import xml.etree.ElementTree as ET
import logging
import json
from dotenv import load_dotenv

# Load settings from a JSON configuration file
def load_config():
    config_path = os.getenv('CONFIG_PATH', '/app/config/config.json')  # Ensure this path is correct
    with open(config_path, 'r') as file:
        config = json.load(file)
    print("Loaded configuration:", config)  # Debug output
    return config

config = load_config()
# Load environment variables
load_dotenv()

# Define global variables based on environment settings
SERVER_TYPE = os.getenv('SERVER_TYPE')
SERVER_URL = os.getenv('SERVER_URL')
SERVER_TOKEN = os.getenv('SERVER_TOKEN')
SONARR_URL = os.getenv('SONARR_URL')
SONARR_API_KEY = os.getenv('SONARR_API_KEY')
LOG_PATH = os.getenv('LOG_PATH', '/app/logs/app.log')


# Set operation-specific settings from config file
GET_OPTION = config['get_option']
ACTION_OPTION = config['action_option']
ALREADY_WATCHED = config['already_watched']

ALWAYS_KEEP = config['always_keep'] 

# Setup logging
logging.basicConfig(filename=LOG_PATH, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


def parse_plex_response(content):
    """Parse XML content from Plex webhook."""
    try:
        root = ET.fromstring(content)
        for video in root.iter('Video'):
            if video.get('type') == 'episode':
                grandparentTitle = video.get('grandparentTitle')
                parentIndex = int(video.get('parentIndex')) if video.get('parentIndex') else None
                index = int(video.get('index')) if video.get('index') else None
                return grandparentTitle, parentIndex, index
    except ET.ParseError as e:
        logging.error(f"XML parsing error: {str(e)}")
    return None, None, None  # Ensure three values are always returned

def get_server_activity():
    """Fetch current viewing details from Plex or Jellyfin."""
    headers = {'X-Plex-Token': SERVER_TOKEN} if SERVER_TYPE == 'plex' else {'Authorization': f'Bearer {SERVER_TOKEN}'}
    activity_url = f"{SERVER_URL}/status/sessions" if SERVER_TYPE == 'plex' else f"{SERVER_URL}/sessions"
    response = requests.get(activity_url, headers=headers)
    if response.ok:
        return parse_plex_response(response.content)
    else:
        logging.error(f"Failed to fetch current activity. Status Code: {response.status_code}")
    return None, None, None  # Default return if the response is not okay



def get_series_id(series_name):
    """Fetch series ID by name from Sonarr."""
    url = f"{SONARR_URL}/api/v3/series"
    headers = {'X-Api-Key': SONARR_API_KEY}
    response = requests.get(url, headers=headers)
    if response.ok:
        series_list = response.json()
        for series in series_list:
            if series['title'].lower() == series_name.lower():
                return series['id']
    else:
        logging.error("Failed to fetch series ID.")
    return None

def get_episode_details(series_id, season_number):
    """Fetch details of episodes for a specific series and season from Sonarr."""
    url = f"{SONARR_URL}/api/v3/episode?seriesId={series_id}&seasonNumber={season_number}"
    headers = {'X-Api-Key': SONARR_API_KEY}
    response = requests.get(url, headers=headers)
    if response.ok:
        episode_details = response.json()
        # Add series title to each episode
        series_title = get_series_title(series_id)
        for episode in episode_details:
            episode['seriesTitle'] = series_title
        return episode_details
    logging.error("Failed to fetch episode details.")
    return []

def get_series_title(series_id):
    """Fetch series title by series ID from Sonarr."""
    url = f"{SONARR_URL}/api/v3/series/{series_id}"
    headers = {'X-Api-Key': SONARR_API_KEY}
    response = requests.get(url, headers=headers)
    if response.ok:
        return response.json()['title']
    logging.error("Failed to fetch series title.")
    return None

def monitor_episodes(episode_ids, monitor=True):
    """Set episodes to monitored or unmonitored in Sonarr."""
    url = f"{SONARR_URL}/api/v3/episode/monitor"
    headers = {'X-Api-Key': SONARR_API_KEY, 'Content-Type': 'application/json'}
    data = {"episodeIds": episode_ids, "monitored": monitor}
    response = requests.put(url, json=data, headers=headers)
    if response.ok:
        logging.info(f"Episodes {episode_ids} set to monitored: {monitor}")
    else:
        logging.error(f"Failed to set episodes to monitored. Response: {response.text}")

def trigger_episode_search_in_sonarr(episode_ids):
    """Trigger a search for specified episodes in Sonarr."""
    url = f"{SONARR_URL}/api/v3/command"
    headers = {'X-Api-Key': SONARR_API_KEY, 'Content-Type': 'application/json'}
    data = {"name": "EpisodeSearch", "episodeIds": episode_ids}
    response = requests.post(url, json=data, headers=headers)
    if response.ok:
        logging.info("Episode search command sent to Sonarr successfully.")
    else:
        logging.error("Failed to send episode search command. Response:", response.text)



def unmonitor_episodes(episode_ids):
    """Unmonitor specified episodes in Sonarr."""
    unmonitor_url = f"{SONARR_URL}/api/v3/episode/monitor"
    unmonitor_data = {"episodeIds": episode_ids, "monitored": False}
    unmonitor_headers = {'X-Api-Key': SONARR_API_KEY, 'Content-Type': 'application/json'}
    response = requests.put(unmonitor_url, json=unmonitor_data, headers=unmonitor_headers)
    if response.ok:
        logging.info(f"Episodes {episode_ids} unmonitored successfully.")
    else:
        logging.error(f"Failed to unmonitor episodes. Response: {response.text}")

def find_episodes_to_delete(episode_details, current_episode_number):
    """Find episodes before the current episode to potentially delete, checking against 'always_keep'."""
    episodes_to_delete = []
    for ep in episode_details:
        if ep['episodeNumber'] < current_episode_number and ep['seriesTitle'] not in ALWAYS_KEEP:
            if ep['episodeFileId'] > 0:  # Ensure there is a file to delete
                episodes_to_delete.append(ep['episodeFileId'])
    return episodes_to_delete

def delete_episodes_in_sonarr(episode_file_ids):
    """Delete specified episodes in Sonarr."""
    for episode_file_id in episode_file_ids:
        url = f"{SONARR_URL}/api/v3/episodeFile/{episode_file_id}"
        headers = {'X-Api-Key': SONARR_API_KEY}
        response = requests.delete(url, headers=headers)
        if response.ok:
            logging.info(f"Successfully deleted episode file with ID: {episode_file_id}")
        else:
            logging.error(f"Failed to delete episode file. Response: {response.text}")
def determine_keep_ids(current_episodes, episode_number, already_watched, always_keep):
    # Keep the most recent episodes as specified by 'already_watched'
    if isinstance(already_watched, int):
        keep_ids = [ep['id'] for ep in sorted(current_episodes, key=lambda x: -x['episodeNumber'])[:already_watched]]
    else:
        # Keep all episodes in the current season if 'already_watched' is set to 'season'
        keep_ids = [ep['id'] for ep in current_episodes]

    # Ensure episodes with titles in 'always_keep' are not deleted
    keep_ids.extend(ep['id'] for ep in current_episodes if ep['seriesTitle'] in always_keep and ep['id'] not in keep_ids)
    return list(set(keep_ids))  # Remove duplicates and return the list

def main():
    series_name, season_number, episode_number = get_server_activity()
    if series_name:
        series_id = get_series_id(series_name)
        if series_id:
            current_season_episodes = get_episode_details(series_id, season_number)
            if current_season_episodes:
                # Filter out episodes that are already past
                remaining_current_season = [ep for ep in current_season_episodes if ep['episodeNumber'] > episode_number]

                # Calculate how many more episodes to fetch based on GET_OPTION
                episodes_needed = config['get_option'] - len(remaining_current_season)
                next_episode_ids = [ep['id'] for ep in remaining_current_season][:config['get_option']]

                # Fetch episodes from next season if more are needed
                if episodes_needed > 0:
                    next_season_episodes = get_episode_details(series_id, season_number + 1)
                    # Only add as many episodes as needed to fulfill the get_option requirement
                    additional_episodes_needed = config['get_option'] - len(next_episode_ids)
                    next_episode_ids.extend([ep['id'] for ep in next_season_episodes][:additional_episodes_needed])

                monitor_episodes(next_episode_ids, monitor=True)
                trigger_episode_search_in_sonarr(next_episode_ids)

                # Handling deletions and unmonitoring based on configuration
                keep_ids = determine_keep_ids(current_season_episodes, episode_number, config['already_watched'], config['always_keep'])
                episodes_to_delete = find_episodes_to_delete(current_season_episodes, episode_number)
                episodes_to_delete = [ep for ep in episodes_to_delete if ep not in keep_ids]
                delete_episodes_in_sonarr(episodes_to_delete)
                
                unmonitor_ids = [ep['id'] for ep in current_season_episodes if ep['id'] not in keep_ids]
                unmonitor_episodes(unmonitor_ids)

            else:
                logging.info("No episodes found for the current series and season.")
        else:
            logging.error("Failed to fetch series ID for the active series.")
    else:
        logging.info("No active series found to process.")

if __name__ == "__main__":
    main()
