import os
import requests
import logging
import json
from dotenv import load_dotenv

# Load settings from a JSON configuration file
def load_config():
    config_path = os.getenv('CONFIG_PATH', '/app/config/config.json')
    with open(config_path, 'r') as file:
        config = json.load(file)
    print("Loaded configuration:", config)
    return config

config = load_config()

# Load environment variables
load_dotenv()

# Define global variables based on environment settings
SONARR_URL = os.getenv('SONARR_URL')
SONARR_API_KEY = os.getenv('SONARR_API_KEY')
LOG_PATH = os.getenv('LOG_PATH', '/app/logs/app.log')
DEBUG_MODE = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

# Setup logging
log_level = logging.DEBUG if DEBUG_MODE else logging.INFO
logging.basicConfig(
    filename=LOG_PATH,
    level=log_level,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Optionally add a console handler if in debug mode
if DEBUG_MODE:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(console_handler)

# Set operation-specific settings from config file
GET_OPTION = config['get_option']
ACTION_OPTION = config['action_option']
ALREADY_WATCHED = config['already_watched']
ALWAYS_KEEP = config['always_keep']

def get_server_activity():
    """Read current viewing details from Tautulli webhook stored data."""
    try:
        with open('/app/temp/data_from_tautulli.json', 'r') as file:
            data = json.load(file)
        series_title = data['plex_title']
        season_number = int(data['plex_season_num'])
        episode_number = int(data['plex_ep_num'])
        logging.debug(f"Fetched server activity: {series_title}, Season: {season_number}, Episode: {episode_number}")
        return series_title, season_number, episode_number
    except Exception as e:
        logging.error(f"Failed to read or parse data from Tautulli webhook: {str(e)}")
    return None, None, None

def send_webhook():
    """Send a webhook request."""
    url = "Http://192.168.254.64:8123/api/webhook/wakeoffice"
    try:
        response = requests.post(url)
        if response.status_code == 200:
            logging.info("Webhook request sent successfully.")
        else:
            logging.error(f"Failed to send webhook request. Status code: {response.status_code}")
    except Exception as e:
        logging.error(f"Failed to send webhook request: {str(e)}")

def get_series_id(series_name):
    """Fetch series ID by name from Sonarr."""
    url = f"{SONARR_URL}/api/v3/series"
    headers = {'X-Api-Key': SONARR_API_KEY}
    attempts = 2  # Total number of attempts to connect

    for attempt in range(attempts):
        try:
            response = requests.get(url, headers=headers)
            if response.ok:
                series_list = response.json()
                for series in series_list:
                    if series['title'].lower() == series_name.lower():
                        return series['id']
            else:
                logging.error(f"Attempt {attempt+1}: Failed to fetch series ID. Server response not OK.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Attempt {attempt+1}: Request failed due to network error: {str(e)}")

        if attempt < attempts - 1:  # If not the last attempt, try to wake the server
            logging.info("Attempting to wake the server...")
            send_webhook()  # Send the webhook request instead of WOL
            logging.info("Waiting for the server to wake up... Retrying in 15 seconds.")
            time.sleep(15)  # Pause the script for 15 seconds to allow the server time to boot

    logging.error("All attempts failed after sending WOL and waiting. The server might be unreachable.")
    return None

def fetch_all_episodes(series_id):
    """Fetch all episodes for a series from Sonarr."""
    all_episodes = []
    url = f"{SONARR_URL}/api/v3/episode?seriesId={series_id}"
    headers = {'X-Api-Key': SONARR_API_KEY}
    response = requests.get(url, headers=headers)
    if response.ok:
        all_episodes = response.json()
    return all_episodes

def monitor_episodes(episode_ids, monitor=True):
    """Set episodes to monitored or unmonitored in Sonarr."""
    if episode_ids:
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
        logging.error(f"Failed to send episode search command. Response: {response.text}")

def find_episodes_to_delete(all_episodes, already_watched, last_watched_id):
    """Find episodes to delete, ensuring they're not in the keep list and have files."""
    episodes_to_delete = []
    if already_watched == "all":
        return episodes_to_delete
    elif already_watched == "season":
        last_watched_season = max(ep['seasonNumber'] for ep in all_episodes if ep['id'] == last_watched_id)
        episodes_to_delete = [ep['episodeFileId'] for ep in all_episodes if ep['seasonNumber'] < last_watched_season and ep['episodeFileId'] > 0]
    elif isinstance(already_watched, int):
        episodes_to_delete = [ep['episodeFileId'] for ep in all_episodes if ep['id'] < last_watched_id and ep['episodeFileId'] > 0]
        episodes_to_delete = episodes_to_delete[:len(episodes_to_delete) - already_watched]

    return episodes_to_delete

def delete_episodes_in_sonarr(episode_file_ids):
    """Delete specified episodes in Sonarr."""
    if not episode_file_ids:
        logging.info("No episodes to delete.")
        return

    failed_deletes = []
    for episode_file_id in episode_file_ids:
        try:
            url = f"{SONARR_URL}/api/v3/episodeFile/{episode_file_id}"
            headers = {'X-Api-Key': SONARR_API_KEY}
            response = requests.delete(url, headers=headers)
            response.raise_for_status()  # Raise an HTTPError for bad responses
            logging.info(f"Successfully deleted episode file with ID: {episode_file_id}")
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err} - Response: {response.text}")
            failed_deletes.append(episode_file_id)
        except Exception as err:
            logging.error(f"Other error occurred: {err}")
            failed_deletes.append(episode_file_id)
    
    if failed_deletes:
        logging.error(f"Failed to delete the following episode files: {failed_deletes}")

def fetch_next_episodes(all_episodes, season_number, episode_number, num_episodes):
    """Fetch the next num_episodes episodes starting from the given season and episode."""
    next_episode_ids = []

    # Get remaining episodes in the current season
    current_season_episodes = [ep for ep in all_episodes if ep['seasonNumber'] == season_number and ep['episodeNumber'] > episode_number]
    next_episode_ids.extend([ep['id'] for ep in current_season_episodes])

    # Fetch episodes from the next seasons if needed
    next_season_number = season_number + 1
    while len(next_episode_ids) < num_episodes:
        next_season_episodes = [ep for ep in all_episodes if ep['seasonNumber'] == next_season_number]
        next_episode_ids.extend([ep['id'] for ep in next_season_episodes])
        next_season_number += 1

    return next_episode_ids[:num_episodes]

def monitor_and_search_episodes(next_episode_ids):
    """Ensure episodes are monitored and trigger search."""
    if next_episode_ids:
        monitor_episodes(next_episode_ids, monitor=True)
        if config['action_option'] == "search":
            trigger_episode_search_in_sonarr(next_episode_ids)

def delete_old_episodes(series_id, keep_episode_ids):
    """Delete old episodes that are not in the keep list."""
    all_episodes = fetch_all_episodes(series_id)
    episodes_with_files = [ep for ep in all_episodes if ep['hasFile']]
    episodes_to_delete = [ep['episodeFileId'] for ep in episodes_with_files if ep['id'] not in keep_episode_ids]
    delete_episodes_in_sonarr(episodes_to_delete)

def is_series_finale(all_episodes, last_watched_id):
    """Check if the last watched episode is the series finale."""
    last_watched_episode = next((ep for ep in all_episodes if ep['id'] == last_watched_id), None)
    if last_watched_episode and last_watched_episode.get('finaleType') == 'series':
        return True
    return False

def monitor_and_search_episodes(next_episode_ids):
    """Ensure episodes are monitored and trigger search."""
    if next_episode_ids:
        monitor_episodes(next_episode_ids, monitor=True)
        if config['action_option'] == "search":
            trigger_episode_search_in_sonarr(next_episode_ids)

def main():
    series_name, season_number, episode_number = get_server_activity()
    if series_name:
        series_id = get_series_id(series_name)
        if series_id:
            all_episodes = fetch_all_episodes(series_id)
            if all_episodes:
                last_watched_id = next(ep['id'] for ep in all_episodes if ep['seasonNumber'] == season_number and ep['episodeNumber'] == episode_number)
                
                # Check if the last watched episode is the series finale
                if is_series_finale(all_episodes, last_watched_id):
                    logging.info("Last watched episode is the series finale. No further episodes to monitor.")
                    next_episode_ids = []
                else:
                    next_episode_ids = fetch_next_episodes(all_episodes, season_number, episode_number, config['get_option'])

                # Ensure next episodes are monitored and trigger search if needed
                monitor_and_search_episodes(next_episode_ids)

                episodes_to_delete = find_episodes_to_delete(all_episodes, config['already_watched'], last_watched_id)
                delete_episodes_in_sonarr(episodes_to_delete)

                keep_episode_ids = next_episode_ids + [last_watched_id]
                delete_old_episodes(series_id, keep_episode_ids)
            else:
                logging.info("No episodes found for the current series.")
        else:
            logging.info(f"Series ID not found for series: {series_name}")
    else:
        logging.info("No server activity found.")

if __name__ == "__main__":
    main()
