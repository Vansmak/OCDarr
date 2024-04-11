import os
import requests
import xml.etree.ElementTree as ET
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define global variables based on environment settings
SERVER_TYPE = os.getenv('SERVER_TYPE')
SERVER_URL = os.getenv('SERVER_URL')
SERVER_TOKEN = os.getenv('SERVER_TOKEN')
SONARR_URL = os.getenv('SONARR_URL')
SONARR_API_KEY = os.getenv('SONARR_API_KEY')
GET_OPTION = os.getenv('GET_OPTION', 'episode')
ACTION_OPTION = os.getenv('ACTION_OPTION', 'search')
ALREADY_WATCHED = os.getenv('ALREADY_WATCHED', 'keep')
LOG_PATH = os.getenv('LOG_PATH', '/app/logs/app.log')

# Setup logging
logging.basicConfig(filename=LOG_PATH, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_plex_response(content):
    """Parse the XML content received from Plex webhook."""
    try:
        root = ET.fromstring(content)
        for video in root.iter('Video'):
            if video.get('type') == 'episode':
                return video.get('grandparentTitle'), int(video.get('parentIndex')), int(video.get('index'))
    except ET.ParseError as e:
        logging.error(f"XML parsing error: {str(e)}")
    return None, None, None

def get_server_activity():
    """Fetch current viewing details from Plex or Jellyfin based on webhook trigger."""
    headers = {'X-Plex-Token': SERVER_TOKEN} if SERVER_TYPE == 'plex' else {'Authorization': f'Bearer {SERVER_TOKEN}'}
    activity_url = f"{SERVER_URL}/status/sessions" if SERVER_TYPE == 'plex' else f"{SERVER_URL}/sessions"
    response = requests.get(activity_url, headers=headers)
    if response.ok:
        return parse_plex_response(response.content)
    else:
        logging.error(f"Failed to fetch current activity from {SERVER_TYPE}. Status Code: {response.status_code}")
    return None, None, None

def get_series_id(series_name):
    """ Fetch series ID by name from Sonarr. """
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
    """ Fetch details of episodes in a given series and season from Sonarr. """
    url = f"{SONARR_URL}/api/v3/episode?seriesId={series_id}&seasonNumber={season_number}"
    headers = {'X-Api-Key': SONARR_API_KEY}
    response = requests.get(url, headers=headers)
    if response.ok:
        return response.json()
    logging.error("Failed to fetch episode details.")
    return []

def monitor_episodes(episode_ids, monitor=True):
    """ Set episodes to monitored or unmonitored in Sonarr. """
    url = f"{SONARR_URL}/api/v3/episode/monitor"
    headers = {'X-Api-Key': SONARR_API_KEY, 'Content-Type': 'application/json'}
    data = {"episodeIds": episode_ids, "monitored": monitor}
    response = requests.put(url, json=data, headers=headers)
    if response.ok:
        logging.info(f"Episodes {episode_ids} set to monitored: {monitor}")
    else:
        logging.error(f"Failed to set episodes {episode_ids} to monitored. Response: {response.text}")

def trigger_episode_search_in_sonarr(episode_ids):
    url = f"{SONARR_URL}/api/v3/command"
    headers = {'X-Api-Key': SONARR_API_KEY, 'Content-Type': 'application/json'}
    data = {"name": "EpisodeSearch", "episodeIds": episode_ids}
    response = requests.post(url, json=data, headers=headers)
    if response.ok:
        logging.info("Episode search command sent to Sonarr successfully.")
    else:
        logging.error("Failed to send episode search command to Sonarr. Response:", response.text)

def find_episodes_to_delete(episode_details, current_episode_number):
    episodes_before_target = [ep for ep in episode_details if ep['episodeNumber'] < int(current_episode_number) - 1]
    return [ep['episodeFileId'] for ep in episodes_before_target if ep['episodeFileId'] > 0]

def delete_episodes_in_sonarr(episode_file_ids):
    for episode_file_id in episode_file_ids:
        url = f"{SONARR_URL}/api/v3/episodeFile/{episode_file_id}"
        headers = {'X-Api-Key': SONARR_API_KEY}
        response = requests.delete(url, headers=headers)
        if response.ok:
            logging.info(f"Successfully deleted episode file with ID: {episode_file_id}")
        else:
            logging.error(f"Failed to delete episode file with ID: {episode_file_id}. Response: {response.text}")

def unmonitor_episode_in_sonarr(episode_id):
    url = f"{SONARR_URL}/api/v3/episode/{episode_id}"  # Corrected endpoint
    headers = {'X-Api-Key': SONARR_API_KEY, 'Content-Type': 'application/json'}
    data = {"monitored": False}
    response = requests.put(url, json=data, headers=headers)
    if response.ok:
        print(f"Episode ID {episode_id} unmonitored successfully.")
    else:
        print(f"Failed to unmonitor episode ID {episode_id}. Response: {response.text}")




def main():
    series_name, season_number, episode_number = get_server_activity()
    if series_name:
        series_id = get_series_id(series_name)
        if series_id:
            current_episodes = get_episode_details(series_id, season_number)
            if current_episodes:
                # Decide which episodes to monitor based on GET_OPTION
                if GET_OPTION == 'season':
                    next_episode_ids = [ep['id'] for ep in current_episodes if ep['episodeNumber'] >= episode_number]
                else:
                    next_episode_ids = [ep['id'] for ep in current_episodes if ep['episodeNumber'] == episode_number + 1]
                monitor_episodes(next_episode_ids, True)
                if ACTION_OPTION == 'search':
                    trigger_episode_search_in_sonarr(next_episode_ids)
                if ALREADY_WATCHED == 'delete':
                    episodes_to_delete = [ep['id'] for ep in current_episodes if ep['episodeNumber'] < episode_number - 1]
                    delete_episodes_in_sonarr(episodes_to_delete)
                    # Delete episodes older than one step back
                    episodes_to_delete_more_than_one_step_back = find_episodes_to_delete(current_episodes, episode_number)
                    delete_episodes_in_sonarr(episodes_to_delete_more_than_one_step_back)
                # Unmonitor the current episode
                unmonitor_episode_in_sonarr(current_episodes[0]['id'])

              

if __name__ == "__main__":
    main()


