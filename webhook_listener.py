from flask import Flask, render_template, request, redirect, url_for, jsonify
import subprocess
import os
import time
import logging
import json
import sonarr_utils
from datetime import datetime
from dotenv import load_dotenv
import requests  # Add this import statement
import modified_episeerr
import threading
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Load environment variables
SONARR_URL = os.getenv('SONARR_URL')
SONARR_API_KEY = os.getenv('SONARR_API_KEY')
MISSING_LOG_PATH = os.getenv('MISSING_LOG_PATH', '/app/logs/missing.log')
LAST_PROCESSED_FILE = os.path.join(os.getcwd(), 'data', 'last_processed.json')
os.makedirs(os.path.dirname(LAST_PROCESSED_FILE), exist_ok=True)

# Setup logging to capture all logs
log_file = os.getenv('LOG_PATH', '/app/logs/app.log')
log_level = logging.INFO  # Capture INFO and ERROR levels

# Create log directory if it doesn't exist
os.makedirs(os.path.dirname(log_file), exist_ok=True)

# Create a RotatingFileHandler
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=1*1024*1024,  # 1 MB max size
    backupCount=2,  # Keep 2 backup files
    encoding='utf-8'
)
file_handler.setLevel(log_level)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Configure the root logger
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[file_handler]
)

# Adding stream handler to also log to console for Docker logs to capture
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG if os.getenv('FLASK_DEBUG', 'false').lower() == 'true' else logging.INFO)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
stream_handler.setFormatter(formatter)
app.logger.addHandler(stream_handler)

# Define the services dictionary
services = {
    "Plex": "http://192.168.254.205:32400/web",
    "Sonarr": "http://192.168.254.205:8989",
    "Radarr": "http://192.168.254.205:7878",
    "Tautulli": "http://192.168.254.205:8181",
    "SABnzbd": "http://192.168.254.205:8080",
    "Prowlarr": "http://192.168.254.205:9696",
    "Jellyseer": "http://192.168.254.205:5055",
    
}

# Configuration management
config_path = os.path.join(app.root_path, 'config', 'config.json')
TIMESTAMP_FILE_PATH = '/app/backgrounds/fanart_timestamp.txt'

def load_config():
    try:
        with open(config_path, 'r') as file:
            config = json.load(file)
        if 'rules' not in config:
            config['rules'] = {}
        return config
    except FileNotFoundError:
        default_config = {
            'rules': {
                'full_seasons': {
                    'get_option': 'season',
                    'action_option': 'monitor',
                    'keep_watched': 'season',
                    'monitor_watched': False,
                    'series': []
                }
            }
        }
        return default_config

def save_config(config):
    with open(config_path, 'w') as file:
        json.dump(config, file, indent=4)

def get_missing_log_content():
    try:
        with open(MISSING_LOG_PATH, 'r') as file:
            return file.read()
    except FileNotFoundError:
        return "No missing entries logged."
    except Exception as e:
        app.logger.error(f"Failed to read missing log: {str(e)}")
        return "Failed to read log."

def add_recent_activity(series_id, title, description):
    """Add a recent activity to the list"""
    activities = []
    
    # Create directory if needed
    os.makedirs(os.path.dirname(ACTIVITIES_FILE), exist_ok=True)
    
    # Load existing activities if available
    try:
        if os.path.exists(ACTIVITIES_FILE):
            with open(ACTIVITIES_FILE, 'r') as f:
                activities = json.load(f)
    except Exception as e:
        app.logger.error(f"Error loading activities: {str(e)}")
    
    # Add new activity at the beginning
    activities.insert(0, {
        'series_id': series_id,
        'title': title,
        'description': description,
        'timestamp': datetime.now().isoformat()
    })
    
    # Limit to max activities
    activities = activities[:MAX_ACTIVITIES]
    
    # Save updated activities
    try:
        with open(ACTIVITIES_FILE, 'w') as f:
            json.dump(activities, f, indent=2)
    except Exception as e:
        app.logger.error(f"Error saving activities: {str(e)}")

def get_recent_activities():
    """Get recent activities with time_ago added"""
    # Just return an empty list to avoid errors
    return []
@app.route('/process-episode-selection', methods=['POST'])
def process_episode_selection():
    """Process selected episodes by monitoring and searching for them"""
    try:
        request_id = request.form.get('request_id')
        episode_numbers = request.form.getlist('episodes')
        action = request.form.get('action', 'process')  # 'process' or 'cancel'
        
        # Load the request
        request_file = os.path.join(modified_episeerr.REQUESTS_DIR, f"{request_id}.json")
        if not os.path.exists(request_file):
            return jsonify({"error": "Request not found"}), 404
        
        with open(request_file, 'r') as f:
            request_data = json.load(f)
        
        series_id = request_data['series_id']
        series_title = request_data['title']
        jellyseerr_request_id = request_data.get('request_id')
        
        if action == 'cancel':
            app.logger.info(f"Cancelling request {request_id} for {series_title}")
            
            # Delete the Jellyseerr request if available
            if jellyseerr_request_id:
                app.logger.info(f"Deleting Jellyseerr request ID: {jellyseerr_request_id}")
                delete_success = modified_episeerr.delete_overseerr_request(jellyseerr_request_id)
                app.logger.info(f"Jellyseerr delete result: {delete_success}")
            
            # Delete the request file
            try:
                os.remove(request_file)
                app.logger.info(f"Removed request file for {series_title}")
            except Exception as e:
                app.logger.error(f"Error removing request file: {str(e)}")
            
            # Redirect to the home page with appropriate message
            return redirect(url_for('home', section='settings', subsection='requests_section', 
                          message=f"Request for {series_title} cancelled"))
        
        # Convert episode numbers to integers
        episode_numbers = [int(num) for num in episode_numbers if num.isdigit()]
        
        if not episode_numbers:
            return jsonify({"error": "No valid episodes selected"}), 400
        
        # Process the episodes using episeerr
        success = modified_episeerr.process_episode_selection(series_id, episode_numbers)
        
        if success:
            # Delete the request file
            os.remove(request_file)
            
            # Delete the Jellyseerr request if available
            if jellyseerr_request_id:
                modified_episeerr.delete_overseerr_request(jellyseerr_request_id)
            # Save the last processed show
            last_processed = {
                'series_id': series_id,
                'title': series_title,
                'season': request_data['season'],
                'timestamp': datetime.now().isoformat(),
                'episode_count': len(episode_numbers)
            }
            
            try:
                with open(LAST_PROCESSED_FILE, 'w') as f:
                    json.dump(last_processed, f, indent=2)
            except Exception as e:
                app.logger.error(f"Error saving last processed show: {str(e)}")

            # Run download check twice to catch any downloads that might be delayed
            app.logger.info("Checking for downloads to cancel after processing request")
            modified_episeerr.check_and_cancel_unmonitored_downloads()
            
            app.logger.info("Running download check again")
            modified_episeerr.check_and_cancel_unmonitored_downloads()
            
            # Redirect to the home page instead of returning JSON
            return redirect(url_for('home', section='settings', subsection='requests_section', 
                           message=f"Processing {len(episode_numbers)} episodes for {series_title}"))
        else:
            return redirect(url_for('home', section='settings', subsection='requests_section', 
                          message=f"Failed to process episodes for {series_title}"))
        
    except Exception as e:
        app.logger.error(f"Error processing episode selection: {str(e)}", exc_info=True)
        return redirect(url_for('home', section='settings', subsection='requests_section', 
                      message="An error occurred while processing episodes"))
# Update the home route to include pending requests
@app.route('/')
def home():
    config = load_config()
    preferences = sonarr_utils.load_preferences()
    current_series = sonarr_utils.fetch_series_and_episodes(preferences)
    upcoming_premieres = sonarr_utils.fetch_upcoming_premieres(preferences)
    all_series = sonarr_utils.get_series_list(preferences)
   
    # Get pending requests from episeerr
    pending_requests = []
    has_pending_requests = False
    try:
        for filename in os.listdir(modified_episeerr.REQUESTS_DIR):
            if filename.endswith('.json'):
                with open(os.path.join(modified_episeerr.REQUESTS_DIR, filename), 'r') as f:
                    request_data = json.load(f)
                    pending_requests.append(request_data)
        # Sort by creation date, newest first
        pending_requests.sort(key=lambda x: x.get('created_at', 0), reverse=True)
        has_pending_requests = len(pending_requests) > 0
    except Exception as e:
        app.logger.error(f"Failed to load pending requests: {str(e)}")
    
    # Get the last processed show
    last_processed_show = None
    try:
        if os.path.exists(LAST_PROCESSED_FILE):
            with open(LAST_PROCESSED_FILE, 'r') as f:
                last_processed = json.load(f)
               
                # Calculate how long ago it was processed
                now = datetime.now()
                processed_time = datetime.fromisoformat(last_processed.get('timestamp', now.isoformat()))
                delta = now - processed_time
               
                # Don't show if it's been more than 15 minutes
                if delta.total_seconds() < 900:  # 15 minutes
                    if delta.seconds >= 60:
                        minutes = delta.seconds // 60
                        time_ago = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
                    else:
                        time_ago = "just now"
                   
                    last_processed['time_ago'] = time_ago
                    last_processed_show = last_processed
    except Exception as e:
        app.logger.error(f"Error loading last processed show: {str(e)}")
   
    # Get recent activities
    recent_activities = get_recent_activities()
   
    rules_mapping = {str(series_id): rule_name for rule_name, details in config['rules'].items() for series_id in details.get('series', [])}
    
    for series in all_series:
        series['assigned_rule'] = rules_mapping.get(str(series['id']), 'None')
        
    missing_log_content = get_missing_log_content()
    rule = request.args.get('rule', 'full_seasons')
    service_status = {name: check_service_status(url) for name, url in services.items()}
   
    # Add the SONARR_API_KEY to the config object so it can be used in templates
    config['sonarr_api_key'] = SONARR_API_KEY
    
    return render_template('index.html', config=config, current_series=current_series,
                           upcoming_premieres=upcoming_premieres, all_series=all_series,
                           sonarr_url=SONARR_URL, missing_log=missing_log_content, rule=rule,
                           service_status=service_status, services=services,
                           pending_requests=pending_requests,
                           has_pending_requests=has_pending_requests,
                           recent_activities=recent_activities,
                           last_processed_show=last_processed_show)
                        
@app.route('/update-settings', methods=['POST'])
def update_settings():
    config = load_config()
    
    rule_name = request.form.get('rule_name')
    if rule_name == 'add_new':
        rule_name = request.form.get('new_rule_name')
        if not rule_name:
            return redirect(url_for('home', section='settings', message="New rule name is required."))
    
    get_option = request.form.get('get_option')
    keep_watched = request.form.get('keep_watched')

    config['rules'][rule_name] = {
        'get_option': get_option,
        'action_option': request.form.get('action_option'),
        'keep_watched': keep_watched,
        'monitor_watched': request.form.get('monitor_watched', 'false').lower() == 'true',
        'series': config['rules'].get(rule_name, {}).get('series', [])
    }
    
    save_config(config)
    return redirect(url_for('home', section='settings', message="Settings updated successfully"))

@app.route('/delete_rule', methods=['POST'])
def delete_rule():
    config = load_config()
    rule_name = request.form.get('rule_name')
    if rule_name and rule_name in config['rules']:
        del config['rules'][rule_name]
        save_config(config)
        return redirect(url_for('home', section='settings', message=f"Rule '{rule_name}' deleted successfully."))
    else:
        return redirect(url_for('home', section='settings', message=f"Rule '{rule_name}' not found."))

@app.route('/assign_rules', methods=['POST'])
def assign_rules():
    config = load_config()
    rule_name = request.form.get('assign_rule_name')
    submitted_series_ids = set(request.form.getlist('series_ids'))

    if rule_name == 'None':
        # Remove series from any rule
        for key, details in config['rules'].items():
            details['series'] = [sid for sid in details.get('series', []) if sid not in submitted_series_ids]
    else:
        # Update the rule's series list to include only those submitted
        if rule_name in config['rules']:
            current_series = set(config['rules'][rule_name]['series'])
            updated_series = current_series.union(submitted_series_ids)
            config['rules'][rule_name]['series'] = list(updated_series)

        # Update other rules to remove the series if it's no longer assigned there
        for key, details in config['rules'].items():
            if key != rule_name:
                # Preserve series not submitted in other rules
                details['series'] = [sid for sid in details.get('series', []) if sid not in submitted_series_ids]

    save_config(config)
    return redirect(url_for('home', section='settings', message="Rules updated successfully."))

@app.route('/unassign_rules', methods=['POST'])
def unassign_rules():
    config = load_config()
    rule_name = request.form.get('assign_rule_name')
    submitted_series_ids = set(request.form.getlist('series_ids'))

    # Update the rule's series list to exclude those submitted
    if rule_name in config['rules']:
        current_series = set(config['rules'][rule_name]['series'])
        updated_series = current_series.difference(submitted_series_ids)
        config['rules'][rule_name]['series'] = list(updated_series)

    save_config(config)
    return redirect(url_for('home', section='settings', message="Rules updated successfully."))

@app.route('/webhook', methods=['POST'])
def handle_server_webhook():
    app.logger.info("Received POST request from Tautulli")
    data = request.json
    if data:
        app.logger.info(f"Webhook received with data: {data}")
        try:
            temp_dir = '/app/temp'
            os.makedirs(temp_dir, exist_ok=True)
            with open(os.path.join(temp_dir, 'data_from_tautulli.json'), 'w') as f:
                json.dump(data, f)
            app.logger.info("Data successfully written to data_from_tautulli.json")
            result = subprocess.run(["python3", "/app/servertosonarr.py"], capture_output=True, text=True)
            if result.stderr:
                app.logger.error("Errors from servertosonarr.py: " + result.stderr)
        except Exception as e:
            app.logger.error(f"Failed to handle data or run script: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
        return jsonify({'status': 'success', 'message': 'Script triggered successfully'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'No data received'}), 400
    
# In webhook_listener.py, modify the process_seerr_webhook function:
@app.route('/seerr-webhook', methods=['POST'])
def process_seerr_webhook():
    """Handle incoming Jellyseerr webhooks and process episode requests."""
    app.logger.info("Received webhook at /seerr-webhook")
    
    # Try to parse the JSON
    try:
        json_data = request.json
        app.logger.debug(f"JSON data: {json.dumps(json_data, indent=2)}")

        # For test notifications, just return success
        if json_data.get('notification_type') == 'TEST_NOTIFICATION':
            return jsonify({
                "status": "success", 
                "message": "Test notification received successfully"
            }), 200
            
        # Extract requested season from extra data
        requested_season = None
        for extra in json_data.get('extra', []):
            if extra.get('name') == 'Requested Seasons':
                requested_season = int(extra.get('value'))
                break
                
        # Process approved TV content
        if ('APPROVED' in json_data.get('notification_type', '').upper() and 
            json_data.get('media', {}).get('media_type') == 'tv'):
            
            tvdb_id = json_data.get('media', {}).get('tvdbId')
            if not tvdb_id:
                app.logger.error("No TVDB ID provided")
                return jsonify({"error": "No TVDB ID"}), 400
                
            # Verify season number
            if not requested_season:
                app.logger.error("Missing required season number")
                return jsonify({"error": "No season specified."}), 400
            
            # Extract request ID
            request_id = json_data.get('request', {}).get('request_id')
            
            # Call the process_series function
            success = modified_episeerr.process_series(tvdb_id, requested_season, request_id)
            
            # Get the series ID from Sonarr
            if success:
                headers = modified_episeerr.get_sonarr_headers()
                series_response = requests.get(
                    f"{modified_episeerr.SONARR_URL}/api/v3/series/lookup?term=tvdbId:{tvdb_id}", 
                    headers=headers
                )
                
                if series_response.ok and series_response.json():
                    series_id = series_response.json()[0]['id']
                    
                    # Automatically select all episodes in the season initially
                    episodes = modified_episeerr.get_series_episodes(series_id, requested_season, headers)
                    episode_numbers = [ep['episodeNumber'] for ep in episodes]
                    
                    # Update pending_selections to include all season episodes
                    modified_episeerr.pending_selections[str(series_id)] = {
                        'title': json_data.get('media', {}).get('title'),
                        'season': requested_season,
                        'selected_episodes': set(episode_numbers)
                    }

                    # Immediately check for downloads to cancel
                    app.logger.info("Checking for downloads to cancel after processing request")
                    modified_episeerr.check_and_cancel_unmonitored_downloads()
                
                    # Run the check again in case downloads weren't ready yet
                    app.logger.info("Running download check again")
                    modified_episeerr.check_and_cancel_unmonitored_downloads()
                    
                    # Schedule an additional check after a minute
                    def delayed_download_check():
                        time.sleep(60)  # Wait for 1 minute
                        app.logger.info("Running delayed download cancellation check")
                        modified_episeerr.check_and_cancel_unmonitored_downloads()
                    
                    # Start the delayed check in a separate thread
                    threading.Thread(target=delayed_download_check, daemon=True).start()
                
                    response = {
                        "status": "success" if success else "failed",
                        "message": "Set up series" if success else "Failed to process series"
                    }
                    return jsonify(response), 200 if success else 500

            app.logger.info("Event ignored - not an approved TV request")
            return jsonify({"message": "Ignored event"}), 200

    except Exception as e:
        app.logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

def check_service_status(url):
    try:
        # Add a longer timeout and use a HEAD request which is lighter
        response = requests.head(url, timeout=3, allow_redirects=True)
        
        # Check for successful status codes
        if response.status_code in [200, 301, 302, 303, 307, 308]:
            return "Online"
    except requests.exceptions.RequestException as e:
        # Log the specific connection error if needed
        app.logger.debug(f"Service check failed for {url}: {str(e)}")
    
    return "Offline"
# Define a regular function (not decorated)
# Update this function in webhook_listener.py
def initialize_episeerr():
    modified_episeerr.create_episode_tag()
    app.logger.info("Created episode tag")
    
    # No need for a separate background thread with a 10-minute delay
    # Just do an initial check
    try:
        modified_episeerr.check_and_cancel_unmonitored_downloads()
    except Exception as e:
        app.logger.error(f"Error in initial download check: {str(e)}")

# Update your main block to call the initialization function
if __name__ == '__main__':
    # Call initialization function before running the app
    initialize_episeerr()
    app.run(host='0.0.0.0', port=5001, debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')
