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
    if 'rules' not in config:
        config['rules'] = {}
    return config

config = load_config()

# Load environment variables
load_dotenv()

# Define global variables based on environment settings
SONARR_URL = os.getenv('SONARR_URL')
SONARR_API_KEY = os.getenv('SONARR_API_KEY')
LOG_PATH = os.getenv('LOG_PATH', '/app/logs/app.log')
MISSING_LOG_PATH = os.getenv('MISSING_LOG_PATH', '/app/logs/missing.log')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
handler = logging.FileHandler(LOG_PATH)
logger.addHandler(handler)
missing_logger = logging.getLogger('missing')
missing_handler = logging.FileHandler(MISSING_LOG_PATH)
missing_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
missing_logger.addHandler(missing_handler)
def get_server_activity():
    """Read current viewing details from Server webhook stored data."""
    try:
        with open('/app/temp/data_from_server.json', 'r') as file:
            data = json.load(file)
            
        # Try Jellyfin format first
        series_title = data.get('server_title')
        season_number = data.get('server_season_num')
        episode_number = data.get('server_ep_num')
        
        # If not found, try Plex/Tautulli format
        if not all([series_title, season_number, episode_number]):
            series_title = data.get('plex_title')
            season_number = data.get('plex_season_num')
            episode_number = data.get('plex_ep_num')
        
        if all([series_title, season_number, episode_number]):
            return series_title, int(season_number), int(episode_number)
            
        logger.error("Could not find required data in either Jellyfin or Plex format")
        logger.debug(f"Data contents: {data}")
        
    except Exception as e:
        logger.error(f"Failed to read or parse data from Server webhook: {str(e)}")
    return None, None, None

def get_series_id(series_name):
    """Fetch series ID by name from Sonarr with flexible matching."""
    logger.info(f"Searching for series: {series_name}")
    url = f"{SONARR_URL}/api/v3/series"
    headers = {'X-Api-Key': SONARR_API_KEY}
    response = requests.get(url, headers=headers)
    if response.ok:
        series_list = response.json()
        
        # Try exact match first
        for series in series_list:
            series_title_no_year = series['title'].split('(')[0].strip().lower()
            if series_title_no_year == series_name.lower():
                return series['id']
            if series['title'].lower() == series_name.lower():
                return series['id']
        
        # Try flexible matching
        search_name = series_name.lower().replace('the ', '').replace(' ', '')
        for series in series_list:
            series_title = series['title'].lower()
            clean_title = series_title.replace('the ', '').replace(' ', '')
            if clean_title == search_name:
                return series['id']
            if '(' in series_title:
                base_title = series_title.split('(')[0].strip()
                clean_base = base_title.replace('the ', '').replace(' ', '')
                if clean_base == search_name:
                    return series['id']
        
        missing_logger.info(f"Series not found in Sonarr: {series_name}")
    else:
        logger.error("Failed to fetch series from Sonarr.")
    return None
def get_episode_details(series_id, season_number):
    """Fetch details of episodes for a specific series and season from Sonarr."""
    url = f"{SONARR_URL}/api/v3/episode?seriesId={series_id}&seasonNumber={season_number}"
    headers = {'X-Api-Key': SONARR_API_KEY}
    response = requests.get(url, headers=headers)
    if response.ok:
        return response.json()
    logger.error("Failed to fetch episode details.")
    return []

def monitor_or_search_episodes(episode_ids, action_option):
    """Either monitor or trigger a search for episodes in Sonarr based on the action_option."""
    monitor_episodes(episode_ids, True)
    if action_option == "search":
        trigger_episode_search_in_sonarr(episode_ids)

def monitor_episodes(episode_ids, monitor=True):
    """Set episodes to monitored or unmonitored in Sonarr."""
    url = f"{SONARR_URL}/api/v3/episode/monitor"
    headers = {'X-Api-Key': SONARR_API_KEY, 'Content-Type': 'application/json'}
    data = {"episodeIds": episode_ids, "monitored": monitor}
    response = requests.put(url, json=data, headers=headers)
    if response.ok:
        action = "monitored" if monitor else "unmonitored"
        logger.info(f"Episodes {episode_ids} successfully {action}.")
    else:
        logger.error(f"Failed to set episodes {action}. Response: {response.text}")

def trigger_episode_search_in_sonarr(episode_ids):
    """Trigger a search for specified episodes in Sonarr."""
    url = f"{SONARR_URL}/api/v3/command"
    headers = {'X-Api-Key': SONARR_API_KEY, 'Content-Type': 'application/json'}
    data = {"name": "EpisodeSearch", "episodeIds": episode_ids}
    response = requests.post(url, json=data, headers=headers)
    if response.ok:
        logger.info("Episode search command sent to Sonarr successfully.")
    else:
        logger.error(f"Failed to send episode search command. Response: {response.text}")

def unmonitor_episodes(episode_ids):
    """Unmonitor specified episodes in Sonarr."""
    monitor_episodes(episode_ids, False)
def find_episodes_to_delete(all_episodes, keep_watched, last_watched_id):
    """Find episodes to delete, ensuring they're not in the keep list and have files."""
    episodes_to_delete = []
    if keep_watched == "all":
        return episodes_to_delete  # Skip deletion logic entirely if "all" is specified.
    elif keep_watched == "season":
        last_watched_season = next(ep['seasonNumber'] for ep in all_episodes if ep['id'] == last_watched_id)
        episodes_to_delete = [ep for ep in all_episodes if ep['seasonNumber'] < last_watched_season and ep['hasFile']]
    elif isinstance(keep_watched, int):
        # Sort episodes by date, keeping only the specified count, including and prior to the last watched.
        sorted_episodes = sorted(all_episodes, key=lambda ep: (ep['seasonNumber'], ep['episodeNumber']), reverse=True)
        last_watched_index = next((i for i, ep in enumerate(sorted_episodes) if ep['id'] == last_watched_id), None)
        keep_range = sorted_episodes[max(0, last_watched_index - keep_watched + 1):last_watched_index + 1]
        keep_ids = {ep['id'] for ep in keep_range}
        episodes_to_delete = [ep for ep in all_episodes if ep['id'] not in keep_ids and ep['hasFile']]

    return [ep['episodeFileId'] for ep in episodes_to_delete if 'episodeFileId' in ep]

def delete_episodes_in_sonarr(episode_file_ids):
    """Delete specified episodes in Sonarr."""
    if not episode_file_ids:
        logger.info("No episodes to delete.")
        return

    failed_deletes = []
    for episode_file_id in episode_file_ids:
        try:
            url = f"{SONARR_URL}/api/v3/episodeFile/{episode_file_id}"
            headers = {'X-Api-Key': SONARR_API_KEY}
            response = requests.delete(url, headers=headers)
            response.raise_for_status()  # Raise an HTTPError for bad responses
            logger.info(f"Successfully deleted episode file with ID: {episode_file_id}")
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err} - Response: {response.text}")
            failed_deletes.append(episode_file_id)
        except Exception as err:
            logger.error(f"Other error occurred: {err}")
            failed_deletes.append(episode_file_id)

    if failed_deletes:
        logger.error(f"Failed to delete the following episode files: {failed_deletes}")

def fetch_next_episodes(series_id, season_number, episode_number, get_option):
    """Fetch the next num_episodes episodes starting from the given season and episode."""
    next_episode_ids = []

    try:
        if get_option == "all":
            # Fetch all episodes from Sonarr
            all_episodes = fetch_all_episodes(series_id)
            next_episode_ids.extend([ep['id'] for ep in all_episodes if ep['seasonNumber'] >= season_number])
            return next_episode_ids
        num_episodes = int(get_option)
        # Get remaining episodes in the current season
        current_season_episodes = get_episode_details(series_id, season_number)
        next_episode_ids.extend([ep['id'] for ep in current_season_episodes if ep['episodeNumber'] > episode_number])

        # Fetch episodes from the next season if needed
        next_season_number = season_number + 1
        while len(next_episode_ids) < num_episodes:
            next_season_episodes = get_episode_details(series_id, next_season_number)
            next_episode_ids.extend([ep['id'] for ep in next_season_episodes])
            next_season_number += 1

        return next_episode_ids[:num_episodes]
    except ValueError:
        if get_option == 'season':
            # Fetch all remaining episodes in the current season
            current_season_episodes = get_episode_details(series_id, season_number)
            next_episode_ids.extend([ep['id'] for ep in current_season_episodes if ep['episodeNumber'] > episode_number])
            return next_episode_ids
        else:
            raise ValueError(f"Invalid get_option value: {get_option}")
def fetch_all_episodes(series_id):
    """Fetch all episodes for a series from Sonarr."""
    url = f"{SONARR_URL}/api/v3/episode?seriesId={series_id}"
    headers = {'X-Api-Key': SONARR_API_KEY}
    response = requests.get(url, headers=headers)
    if response.ok:
        return response.json()
    logger.error("Failed to fetch all episodes.")
    return []

def delete_old_episodes(series_id, keep_episode_ids, rule):
    """Delete old episodes that are not in the keep list."""
    all_episodes = fetch_all_episodes(series_id)
    episodes_with_files = [ep for ep in all_episodes if ep['hasFile']]

    keep_watched = rule.get('keep_watched', 'all')

    if keep_watched == "all":
        logger.info("No episodes to delete as keep_watched is set to 'all'.")
        return

    if keep_watched == "season":
        last_watched_season = max(ep['seasonNumber'] for ep in all_episodes if ep['id'] in keep_episode_ids)
        episodes_to_delete = [ep['episodeFileId'] for ep in episodes_with_files if ep['seasonNumber'] < last_watched_season and ep['id'] not in keep_episode_ids]
    else:
        episodes_to_delete = [ep['episodeFileId'] for ep in episodes_with_files if ep['id'] not in keep_episode_ids]

    delete_episodes_in_sonarr(episodes_to_delete)

def process_episodes_based_on_rules(series_id, season_number, episode_number, rule):
    """Fetch, monitor/search, and delete episodes based on defined rules."""
    all_episodes = fetch_all_episodes(series_id)
    last_watched_id = next(ep['id'] for ep in all_episodes if ep['seasonNumber'] == season_number and ep['episodeNumber'] == episode_number)

    if not rule['monitor_watched']:
        unmonitor_episodes([last_watched_id])

    next_episode_ids = fetch_next_episodes(series_id, season_number, episode_number, rule['get_option'])
    monitor_or_search_episodes(next_episode_ids, rule['action_option'])

    episodes_to_delete = find_episodes_to_delete(all_episodes, rule['keep_watched'], last_watched_id)
    delete_episodes_in_sonarr(episodes_to_delete)

    if rule['keep_watched'] != "all":
        keep_episode_ids = next_episode_ids + [last_watched_id]
        delete_old_episodes(series_id, keep_episode_ids, rule)
def apply_default_rule_to_new_series(series_id):
    """Apply default rule to a newly added series, handling monitored season(s)."""
    config = load_config()
    default_rule = config.get('default_rule', '1n1')
    rule = config['rules'].get(default_rule)
    
    if not rule:
        logger.error(f"Default rule '{default_rule}' not found in configuration")
        return
        
    apply_rule_to_series(series_id, rule)
def cancel_downloads_after_episode(series_id, season_number, cutoff_episode):
    """Cancel any active downloads for episodes after the specified episode."""
    url = f"{SONARR_URL}/api/v3/queue"
    headers = {'X-Api-Key': SONARR_API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        if not response.ok:
            logger.error(f"Failed to get queue: {response.text}")
            return
            
        queue_data = response.json()
        if not isinstance(queue_data, dict) or 'records' not in queue_data:
            logger.error("Unexpected queue data format")
            return
            
        # Find matching downloads that are still in progress
        for item in queue_data['records']:
            try:
                # Skip completed downloads
                if item.get('status') == 'completed':
                    continue
                    
                # Check if this is a download for our series and season
                episode = item.get('episode', {})
                if (item.get('seriesId') == series_id and 
                    episode.get('seasonNumber') == season_number and 
                    episode.get('episodeNumber', 0) > cutoff_episode):
                    
                    queue_item_id = item.get('id')
                    if not queue_item_id:
                        continue
                        
                    # Cancel the download
                    cancel_url = f"{SONARR_URL}/api/v3/queue/{queue_item_id}"
                    cancel_response = requests.delete(
                        cancel_url, 
                        headers=headers,
                        params={'removeFromClient': 'true', 'blocklist': False}
                    )
                    
                    ep_num = episode.get('episodeNumber')
                    if cancel_response.ok:
                        logger.info(f"Cancelled in-progress download for S{season_number}E{ep_num}")
                    else:
                        logger.error(f"Failed to cancel download for S{season_number}E{ep_num}: {cancel_response.text}")
                        
            except Exception as item_error:
                logger.error(f"Error processing queue item: {str(item_error)}")
                continue
                
    except Exception as e:
        logger.error(f"Error cancelling downloads: {str(e)}")
        return
def apply_rule_to_series(series_id, rule):
    """Apply specified rule to a series, handling monitored season(s)."""
    url = f"{SONARR_URL}/api/v3/episode?seriesId={series_id}"
    headers = {'X-Api-Key': SONARR_API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        if response.ok:
            episodes = response.json()
            
            # Group monitored episodes by season
            monitored_seasons = {}
            for ep in episodes:
                if ep['monitored']:
                    season = ep['seasonNumber']
                    if season not in monitored_seasons:
                        monitored_seasons[season] = []
                    monitored_seasons[season].append(ep)
            
            if not monitored_seasons:
                logger.info(f"No monitored seasons found for series {series_id}")
                return
                
            logger.info(f"Found monitored seasons: {list(monitored_seasons.keys())}")
            
            # Process each monitored season
            for season_number, season_episodes in monitored_seasons.items():
                if season_number == 0:  # Skip specials
                    continue
                    
                # Sort episodes by number
                season_episodes.sort(key=lambda x: x['episodeNumber'])
                
                logger.info(f"Processing season {season_number}")
                
                # Apply rule based on get_option
                if rule['get_option'] == '1':  # Only monitor first episode
                    for ep in season_episodes:
                        should_monitor = ep['episodeNumber'] == 1
                        monitor_episodes([ep['id']], should_monitor)
                        logger.info(f"{'Monitoring' if should_monitor else 'Unmonitoring'} S{season_number}E{ep['episodeNumber']}")
                        
                elif rule['get_option'] == 'season':
                    # Monitor all episodes in season
                    episode_ids = [ep['id'] for ep in season_episodes]
                    monitor_episodes(episode_ids, True)
                    
                elif rule['get_option'].isdigit():
                    # Monitor specified number of episodes
                    num_episodes = int(rule['get_option'])
                    for i, ep in enumerate(season_episodes):
                        should_monitor = i < num_episodes
                        monitor_episodes([ep['id']], should_monitor)
                
    except Exception as e:
        logger.error(f"Error applying rule to series: {str(e)}")

def get_rule_by_tags(series_tags):
    """Get matching rule based on series tags."""
    config = load_config()
    
    # Check if any tags match rule names
    for tag in series_tags:
        if tag in config['rules']:
            return config['rules'][tag]
    
    # Return default rule if no match found
    default_rule = config.get('default_rule', '1n1')
    return config['rules'].get(default_rule)

def main():
    series_name, season_number, episode_number = get_server_activity()
    
    if series_name:
        series_id = get_series_id(series_name)
        if series_id:
            # Find the specific rule for the series, else apply the default rule
            rule = next((details for key, details in config['rules'].items() 
                        if str(series_id) in details.get('series', [])), None)
            
            if not rule:
                rule = config['rules'].get(config.get('default_rule', '1n1'))
                logger.info(f"No specific rule found for series ID {series_id}. Applying default rule: {rule}")
            
            if rule:
                process_episodes_based_on_rules(series_id, season_number, episode_number, rule)
            else:
                logger.warning(f"No rule found for series ID {series_id}. Skipping operations.")
        else:
            logger.error(f"Series ID not found for series: {series_name}")
    else:
        logger.error("No server activity found.")

if __name__ == "__main__":
    main()

