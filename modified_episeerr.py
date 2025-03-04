# modified_episeerr.py
import os
import json
import time
import requests
import logging
import threading
import re
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
# In modified_episeerr.py
REQUESTS_DIR = os.path.join(os.getcwd(), 'requests')
# Create logs directory in the current working directory
log_dir = os.path.join(os.getcwd(), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'episeerr.log')

# Create logger
logger = logging.getLogger("episeerr")
logger.setLevel(logging.DEBUG)

# Clear any existing handlers
logger.handlers.clear()

# Create rotating file handler
file_handler = RotatingFileHandler(
    log_file, 
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=1,  # Keep one backup file
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(file_formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Sonarr connection details
SONARR_URL = os.getenv('SONARR_URL', 'http://sonarr:8989')
SONARR_API_KEY = os.getenv('SONARR_API_KEY')

# Global variables
EPISODES_TAG_ID = None  # Will be set when create_episode_tag() is called

# Directory to store pending requests
REQUESTS_DIR = os.path.join(os.getcwd(), 'data', 'requests')
os.makedirs(REQUESTS_DIR, exist_ok=True)

# Store pending episode selections
# Format: {series_id: {'title': 'Series Title', 'season': 1, 'episodes': [1, 2, 3, ...]}}
pending_selections = {}

def get_sonarr_headers():
    """Get headers for Sonarr API requests."""
    return {
        'X-Api-Key': SONARR_API_KEY,
        'Content-Type': 'application/json'
    }

def create_episode_tag():
    """Create a single 'episodes' tag in Sonarr and return its ID."""
    try:
        headers = get_sonarr_headers()
        logger.debug(f"Making request to {SONARR_URL}/api/v3/tag")
        
        # Get existing tags
        tags_response = requests.get(
            f"{SONARR_URL}/api/v3/tag",
            headers=headers
        )
        
        if not tags_response.ok:
            logger.error(f"Failed to get tags. Status: {tags_response.status_code}")
            return None

        # Look for existing episodes tag
        episodes_tag_id = None
        for tag in tags_response.json():
            if tag['label'].lower() == 'episodes':
                episodes_tag_id = tag['id']
                logger.info(f"Found existing 'episodes' tag with ID {episodes_tag_id}")
                break
        
        # Create episodes tag if it doesn't exist
        if episodes_tag_id is None:
            tag_create_response = requests.post(
                f"{SONARR_URL}/api/v3/tag",
                headers=headers,
                json={"label": "episodes"}
            )
            if tag_create_response.ok:
                episodes_tag_id = tag_create_response.json().get('id')
                logger.info(f"Created tag: 'episodes' with ID {episodes_tag_id}")
            else:
                logger.error(f"Failed to create episodes tag. Status: {tag_create_response.status_code}")
                return None
        
        # Store the episodes tag ID in a global variable for later use
        global EPISODES_TAG_ID
        EPISODES_TAG_ID = episodes_tag_id
        return episodes_tag_id
    except Exception as e:
        logger.error(f"Error creating episode tag: {str(e)}")
        return None

def unmonitor_season(series_id, season_number, headers):
    """Unmonitor all episodes in a specific season."""
    try:
        # Get episodes for the specific season
        episodes_response = requests.get(
            f"{SONARR_URL}/api/v3/episode?seriesId={series_id}&seasonNumber={season_number}",
            headers=headers
        )
        
        if not episodes_response.ok:
            logger.error(f"Failed to get episodes. Status: {episodes_response.status_code}")
            return False

        episodes = episodes_response.json()
        season_episode_ids = [ep['id'] for ep in episodes]
        
        if season_episode_ids:
            unmonitor_response = requests.put(
                f"{SONARR_URL}/api/v3/episode/monitor",
                headers=headers,
                json={"episodeIds": season_episode_ids, "monitored": False}
            )
            
            if not unmonitor_response.ok:
                logger.error(f"Failed to unmonitor episodes. Status: {unmonitor_response.status_code}")
                return False
            else:
                logger.info(f"Unmonitored all episodes in series ID {series_id} season {season_number}")
                return True
        else:
            logger.info(f"No episodes found for series ID {series_id} season {season_number}")
            return True
            
    except Exception as e:
        logger.error(f"Error unmonitoring season: {str(e)}", exc_info=True)
        return False

def get_episode_info(episode_id, headers):
    """Get episode information from Sonarr API"""
    try:
        response = requests.get(f"{SONARR_URL}/api/v3/episode/{episode_id}", headers=headers)
        if response.ok:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"Error getting episode info: {str(e)}")
        return None

def get_series_title(series_id, headers):
    """Get series title from Sonarr API"""
    try:
        response = requests.get(f"{SONARR_URL}/api/v3/series/{series_id}", headers=headers)
        if response.ok:
            return response.json().get('title', 'Unknown Series')
        return 'Unknown Series'
    except Exception as e:
        logger.error(f"Error getting series title: {str(e)}")
        return 'Unknown Series'

def cancel_download(queue_id, headers):
    """Cancel a download in Sonarr's queue"""
    try:
        # Primary method: Bulk remove with client removal
        payload = {
            "ids": [queue_id],
            "removeFromClient": True,
            "removeFromDownloadClient": True
        }
        response = requests.delete(f"{SONARR_URL}/api/v3/queue/bulk", headers=headers, json=payload)
        
        # If primary method fails, try alternative
        if not response.ok:
            logger.warning(f"Bulk removal failed for queue item {queue_id}. Trying alternative method.")
            response = requests.delete(
                f"{SONARR_URL}/api/v3/queue/{queue_id}", 
                headers=headers,
                params={
                    "removeFromClient": "true"
                }
            )
        
        return response.ok
    except Exception as e:
        logger.error(f"Error cancelling download: {str(e)}")
        return False

def monitor_specific_episodes(series_id, season_number, episode_numbers, headers):
    """
    Monitor specific episodes in a series season.
    
    :param series_id: Sonarr series ID
    :param season_number: Season number
    :param episode_numbers: List of episode numbers to monitor
    :param headers: Sonarr API headers
    :return: True if successful, False otherwise
    """
    try:
        episodes_response = requests.get(
            f"{SONARR_URL}/api/v3/episode?seriesId={series_id}",
            headers=headers
        )
        
        if not episodes_response.ok:
            logger.error(f"Failed to get episodes. Status: {episodes_response.status_code}")
            return False

        episodes = episodes_response.json()
        target_episodes = [
            ep for ep in episodes 
            if ep['seasonNumber'] == season_number and 
            ep['episodeNumber'] in episode_numbers
        ]
        
        if not target_episodes:
            logger.error(f"Target episodes {episode_numbers} not found in season {season_number}")
            return False
        
        monitor_episode_ids = [ep['id'] for ep in target_episodes]
        monitor_response = requests.put(
            f"{SONARR_URL}/api/v3/episode/monitor",
            headers=headers,
            json={"episodeIds": monitor_episode_ids, "monitored": True}
        )
        
        if not monitor_response.ok:
            logger.error(f"Failed to monitor episodes. Status: {monitor_response.status_code}")
            return False
        else:
            logger.info(f"Monitoring episodes {episode_numbers} in season {season_number}")
            return True
    
    except Exception as e:
        logger.error(f"Error monitoring specific episodes: {str(e)}", exc_info=True)
        return False

def search_episodes(series_id, episode_ids, headers):
    """
    Trigger a search for specific episodes in Sonarr.
    
    :param series_id: Sonarr series ID
    :param episode_ids: List of episode IDs to search for
    :param headers: Sonarr API headers
    :return: True if successful, False otherwise
    """
    try:
        if not episode_ids:
            logger.error("No episode IDs provided for search")
            return False
            
        logger.info(f"Searching for episodes: {episode_ids}")
            
        search_payload = {
            "name": "EpisodeSearch",
            "episodeIds": episode_ids
        }
        
        search_response = requests.post(
            f"{SONARR_URL}/api/v3/command",
            headers=headers,
            json=search_payload
        )
        
        if search_response.ok:
            logger.info(f"Triggered search for episodes {episode_ids}")
            return True
        else:
            logger.error(f"Failed to trigger search. Status: {search_response.status_code}")
            logger.error(f"Response content: {search_response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error searching for episodes: {str(e)}", exc_info=True)
        return False

def get_series_episodes(series_id, season_number, headers):
    """
    Get all episodes for a specific series and season.
    
    :param series_id: Sonarr series ID
    :param season_number: Season number
    :param headers: Sonarr API headers
    :return: List of episodes or empty list on failure
    """
    try:
        episodes_response = requests.get(
            f"{SONARR_URL}/api/v3/episode?seriesId={series_id}&seasonNumber={season_number}",
            headers=headers
        )
        
        if not episodes_response.ok:
            logger.error(f"Failed to get episodes. Status: {episodes_response.status_code}")
            return []

        return episodes_response.json()
        
    except Exception as e:
        logger.error(f"Error getting series episodes: {str(e)}", exc_info=True)
        return []

def get_overseerr_headers():
    """Get headers for Overseerr API requests."""
    return {
        'X-Api-Key': os.getenv('OVERSEERR_API_KEY'),
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

def delete_overseerr_request(request_id):
    """
    Delete a specific request in Overseerr.
    
    :param request_id: ID of the request to delete
    :return: True if successful, False otherwise
    """
    try:
        overseerr_url = os.getenv('OVERSEERR_URL')
        headers = get_overseerr_headers()
        
        # Log the deletion attempt
        logger.info(f"Attempting to delete Jellyseerr request {request_id}")
        logger.debug(f"Overseerr headers: {headers}")

        delete_response = requests.delete(
            f"{overseerr_url}/api/v1/request/{request_id}",
            headers=headers
        )
        
        # Log full response for debugging
        logger.debug(f"Delete Request Response Status: {delete_response.status_code}")
        try:
            response_json = delete_response.json()
            logger.debug(f"Delete Request Response JSON: {json.dumps(response_json, indent=2)}")
        except ValueError:
            logger.debug(f"Delete Request Response Text: {delete_response.text}")
        
        if delete_response.ok or delete_response.status_code == 404:
            # 404 means the request was already deleted
            logger.info(f"Successfully deleted or request not found: {request_id}")
            return True
        else:
            logger.error(f"Failed to delete request {request_id}. Status: {delete_response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"Error deleting Jellyseerr request: {str(e)}", exc_info=True)
        return False

def process_episode_selection(series_id, episode_numbers):
    """
    Process selected episodes by monitoring and searching for them.
    
    :param series_id: Sonarr series ID
    :param episode_numbers: List of episode numbers to process
    """
    try:
        series_id = int(series_id)
        headers = get_sonarr_headers()
        
        # Get series info
        series_response = requests.get(
            f"{SONARR_URL}/api/v3/series/{series_id}",
            headers=headers
        )
        
        if not series_response.ok:
            logger.error(f"Failed to get series. Status: {series_response.status_code}")
            return False
            
        series = series_response.json()
         # Debug: Check the global pending_selections dictionary
        logger.info(f"Current pending_selections: {pending_selections}")
         # Find the season even if not in pending_selections
        if str(series_id) not in pending_selections:
            logger.error(f"No pending selection found for series {series_id}")
            
            # Look through requests directory for this series
            for filename in os.listdir(REQUESTS_DIR):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(REQUESTS_DIR, filename), 'r') as f:
                            request_data = json.load(f)
                            if request_data.get('series_id') == series_id:
                                season_number = request_data.get('season')
                                logger.info(f"Found season {season_number} from request file for series {series_id}")
                                # Store in pending selections for later processing
                                pending_selections[str(series_id)] = {
                                    'title': series['title'],
                                    'season': season_number,
                                    'episodes': [],
                                    'selected_episodes': set(episode_numbers)
                                }
                                break
                    except Exception as e:
                        logger.error(f"Error reading request file: {str(e)}")
            
            # If still not found, try to get the current season
            if str(series_id) not in pending_selections:
                # Get the latest season
                seasons_response = requests.get(
                    f"{SONARR_URL}/api/v3/series/{series_id}",
                    headers=headers
                )
                
                if seasons_response.ok:
                    series_data = seasons_response.json()
                    if 'seasons' in series_data and series_data['seasons']:
                        # Find the highest season number
                        seasons = sorted([s.get('seasonNumber', 0) for s in series_data['seasons']])
                        if seasons:
                            season_number = seasons[-1]  # Get the highest season
                            logger.info(f"Using latest season {season_number} for series {series_id}")
                            
                            # Store in pending selections
                            pending_selections[str(series_id)] = {
                                'title': series['title'],
                                'season': season_number,
                                'episodes': [],
                                'selected_episodes': set(episode_numbers)
                            }
        if str(series_id) not in pending_selections:
            logger.error(f"No pending selection found for series {series_id}")
            return False
            
        season_number = pending_selections[str(series_id)]['season']
        
        logger.info(f"Processing episode selection for {series['title']} Season {season_number}: {episode_numbers}")
        
        # Get episode IDs for searching
        episodes = get_series_episodes(series_id, season_number, headers)
        
        if not episodes:
            logger.error(f"No episodes found for series {series_id} season {season_number}")
            return False
        
        # Filter to only valid episode numbers
        valid_episode_numbers = []
        for num in episode_numbers:
            if any(ep['episodeNumber'] == num for ep in episodes):
                valid_episode_numbers.append(num)
            else:
                logger.warning(f"Episode {num} not found in {series['title']} Season {season_number}")
        
        if not valid_episode_numbers:
            logger.error(f"No valid episodes found for selection {episode_numbers}")
            return False
            
        # Monitor selected episodes
        monitor_success = monitor_specific_episodes(
            series_id, 
            season_number, 
            valid_episode_numbers, 
            headers
        )
        
        if not monitor_success:
            logger.error(f"Failed to monitor episodes for series {series_id}")
            return False
            
        # Get episode IDs for searching
        episode_ids = [
            ep['id'] for ep in episodes 
            if ep['episodeNumber'] in valid_episode_numbers
        ]
        
        if not episode_ids:
            logger.error(f"Failed to find episode IDs for {valid_episode_numbers}")
            return False
        
        # Log episode IDs for debugging
        logger.info(f"Episode IDs for search: {episode_ids}")
        
        # Trigger search for the episodes
        search_success = search_episodes(series_id, episode_ids, headers)
        
        if search_success:
            logger.info(f"Successfully set up monitoring and search for {len(valid_episode_numbers)} episodes")
            return True
        else:
            logger.error(f"Failed to search for episodes")
            return False
            
    except Exception as e:
        logger.error(f"Error processing episode selection: {str(e)}", exc_info=True)
        return False

def check_and_cancel_unmonitored_downloads():
    """
    Check and cancel unmonitored episode downloads with enhanced logging.
    """
    headers = get_sonarr_headers()
    
    logger.info("Starting unmonitored download cancellation check")
    logger.info(f"Episodes tag ID: {EPISODES_TAG_ID}")
    
    try:
        # Retrieve current queue
        queue_response = requests.get(f"{SONARR_URL}/api/v3/queue", headers=headers)
        
        if not queue_response.ok:
            logger.error(f"Failed to retrieve queue. Status: {queue_response.status_code}")
            return
        
        queue = queue_response.json().get('records', [])
        logger.info(f"Total queue items: {len(queue)}")
        
        if len(queue) == 0:
            logger.info("No items in queue to process")
            return
            
        # Track cancelled items
        cancelled_count = 0
        
        for item in queue:
            # Detailed logging for each queue item
            logger.info(f"Examining queue item: {item.get('title', 'Unknown')}")
            logger.info(f"Series ID: {item.get('seriesId')}, Episode ID: {item.get('episodeId')}")
            
            # Check if this is a TV episode
            if item.get('seriesId') and item.get('episodeId'):
                # Get series details to check for 'episodes' tag
                series_response = requests.get(
                    f"{SONARR_URL}/api/v3/series/{item['seriesId']}", 
                    headers=headers
                )
                
                if not series_response.ok:
                    logger.error(f"Failed to get series details for ID {item['seriesId']}")
                    continue
                
                series = series_response.json()
                
                # Log series tags
                logger.info(f"Series tags: {series.get('tags', [])}")
                
                # Check if series has 'episodes' tag
                if EPISODES_TAG_ID in series.get('tags', []):
                    # Get episode details
                    episode_info = get_episode_info(item['episodeId'], headers)
                    
                    if episode_info:
                        logger.info(f"Episode details: Number {episode_info.get('episodeNumber')}, Monitored: {episode_info.get('monitored')}")
                        
                        # Check pending_selections for this series first
                        series_id_str = str(item.get('seriesId'))
                        if series_id_str in pending_selections:
                            series_info = pending_selections[series_id_str]
                            selected_episodes = series_info.get('selected_episodes', set())
                            episode_number = episode_info.get('episodeNumber')
                            
                            # If this episode is not in selected episodes, cancel it
                            if episode_number not in selected_episodes:
                                logger.info(f"Episode {episode_number} not in selected episodes {selected_episodes}. Cancelling download.")
                                cancel_success = cancel_download(item['id'], headers)
                                
                                if cancel_success:
                                    series_title = series.get('title', 'Unknown Series')
                                    logger.info(
                                        f"Cancelled download for non-selected episode: "
                                        f"{series_title} - Season {item.get('seasonNumber')} "
                                        f"Episode {episode_info.get('episodeNumber')}"
                                    )
                                    cancelled_count += 1
                                else:
                                    logger.error(f"Failed to cancel download for {series.get('title')} - Episode ID {item['episodeId']}")
                                continue
                        
                        # If not in pending_selections or if the episode is selected, check monitored status
                        if not episode_info.get('monitored', False):
                            # Unmonitored episode - cancel download
                            cancel_success = cancel_download(item['id'], headers)
                            
                            if cancel_success:
                                series_title = series.get('title', 'Unknown Series')
                                logger.info(
                                    f"Cancelled unmonitored download for tagged series: "
                                    f"{series_title} - Season {item.get('seasonNumber')} "
                                    f"Episode {episode_info.get('episodeNumber')}"
                                )
                                cancelled_count += 1
                            else:
                                logger.error(f"Failed to cancel download for {series.get('title')} - Episode ID {item['episodeId']}")
                        else:
                            logger.info(f"Episode {episode_info.get('episodeNumber')} is monitored - keeping download")
                    else:
                        logger.warning(f"Could not get episode info for ID {item['episodeId']}")
                else:
                    logger.info(f"Series {series.get('title')} does not have the episodes tag - skipping")
        
        # Log summary
        logger.info(f"Cancellation check complete. Cancelled {cancelled_count} unmonitored downloads for tagged series")
    
    except Exception as e:
        logger.error(f"Error in download queue monitoring: {str(e)}", exc_info=True)

def save_request(series_id, title, season, episodes, request_id=None):
    """
    Save a request for episode selection to the requests directory.
    
    :param series_id: Sonarr series ID
    :param title: Series title
    :param season: Season number
    :param episodes: List of episode dictionaries
    :param request_id: Optional Jellyseerr request ID
    :return: Request ID string
    """
    try:
        # Create simplified episode list for display
        episode_list = [
            {
                'episodeNumber': ep.get('episodeNumber'),
                'title': ep.get('title', 'Unknown'),
                'id': ep.get('id')
            }
            for ep in episodes
        ]
        
        # Create request entry
        request_entry = {
            'id': f"{series_id}_{season}_{int(time.time())}",
            'series_id': series_id,
            'title': title,
            'season': season,
            'episodes': episode_list,
            'request_id': request_id,
            'selected_episodes': [],
            'created_at': int(time.time())
        }
        
        # Ensure the requests directory exists
        os.makedirs(REQUESTS_DIR, exist_ok=True)
        
        # Save request entry
        filename = f"{request_entry['id']}.json"
        with open(os.path.join(REQUESTS_DIR, filename), 'w') as f:
            json.dump(request_entry, f, indent=2)
        
        logger.info(f"Created request entry for {title} Season {season}")
        
        return request_entry['id']
        
    except Exception as e:
        logger.error(f"Error saving request: {str(e)}", exc_info=True)
        return None

def process_series(tvdb_id, season_number, request_id=None):
    """
    Process a series request from Jellyseerr.
    
    :param tvdb_id: TVDB ID of the series
    :param season_number: Season number requested
    :param request_id: Optional Jellyseerr request ID
    :return: True if successful, False otherwise
    """
    headers = get_sonarr_headers()
    
    for attempt in range(12):  # Max 12 attempts
        try:
            logger.info(f"Checking for series (attempt {attempt + 1}/12)")
            response = requests.get(f"{SONARR_URL}/api/v3/series", headers=headers)
            
            if not response.ok:
                logger.error(f"Failed to get series list. Status: {response.status_code}")
                time.sleep(5)
                continue

            series_list = response.json()
            matching_series = [s for s in series_list if str(s.get('tvdbId')) == str(tvdb_id)]
            
            if not matching_series:
                logger.warning(f"No matching series found for TVDB ID {tvdb_id}")
                time.sleep(5)
                continue

            series = matching_series[0]
            series_id = series['id']
            
            # Check if series has episodes tag
            if EPISODES_TAG_ID not in series.get('tags', []):
                logger.info(f"Series {series['title']} does not have 'episodes' tag. Skipping.")
                return False

            logger.info(f"Found series: {series['title']} (ID: {series_id})")
            
            # 1. Unmonitor episodes only for the requested season
            unmonitor_success = unmonitor_season(series_id, season_number, headers)
            
            if not unmonitor_success:
                logger.error(f"Failed to unmonitor season {season_number} for series {series_id}")
                return False

            # Get episodes for the season
            episodes = get_series_episodes(series_id, season_number, headers)
            
            if not episodes:
                logger.warning(f"No episodes found for {series['title']} Season {season_number}")
                return False
            
            # Sort episodes by episode number
            episodes.sort(key=lambda ep: ep.get('episodeNumber', 0))
            
            # Save the request for web UI
            request_id_string = save_request(
                series_id,
                series['title'],
                season_number,
                episodes,
                request_id
            )
            
            if not request_id_string:
                logger.error(f"Failed to save request for {series['title']} Season {season_number}")
                return False
                
            logger.info(f"Successfully processed request for {series['title']} Season {season_number}")
            
            # Store in pending selections for later processing
            pending_selections[str(series_id)] = {
                'title': series['title'],
                'season': season_number,
                'episodes': episodes,
                'selected_episodes': set()
            }
            
            return True
            
        except Exception as e:
            logger.error(f"Error during processing: {str(e)}", exc_info=True)
            
        time.sleep(5)
    
    logger.error(f"Series not found after 12 attempts")
    return False

# Initialize on import
create_episode_tag()