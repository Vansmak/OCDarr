from flask import Flask, render_template, request, redirect, url_for, jsonify
import subprocess
import os
import logging
import json
import sonarr_utils
from datetime import datetime
from dotenv import load_dotenv
import requests

app = Flask(__name__)

# Setup logging before other operations
logging.basicConfig(
    filename=os.getenv('LOG_PATH', '/app/logs/app.log'), 
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Using only one handler to avoid duplicate logs
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

# Load environment variables from .env file
load_dotenv()

# Load environment variables
SONARR_URL = os.getenv('SONARR_URL')
SONARR_API_KEY = os.getenv('SONARR_API_KEY')
MISSING_LOG_PATH = os.getenv('MISSING_LOG_PATH', '/app/logs/missing.log')
CLIENT_ONLY = os.getenv('CLIENT_ONLY', 'false').lower() == 'true'

def get_tag_mapping():
    """Retrieve existing tags from Sonarr."""
    try:
        response = requests.get(f"{SONARR_URL}/api/v3/tag", headers={'X-Api-Key': SONARR_API_KEY})
        if response.ok:
            return {tag['id']: tag['label'] for tag in response.json()}
        else:
            logger.error("Failed to retrieve Sonarr tags")
    except Exception as e:
        logger.error(f"Error retrieving Sonarr tags: {str(e)}")
    return {}

def create_tag_in_sonarr(tag_name):
    """Create a new tag in Sonarr."""
    try:
        response = requests.post(
            f"{SONARR_URL}/api/v3/tag",
            headers={'X-Api-Key': SONARR_API_KEY, 'Content-Type': 'application/json'},
            json={"label": tag_name}
        )
        if response.ok:
            logger.info(f"Created Sonarr tag: {tag_name}")
            return response.json().get('id')
        else:
            logger.error("Failed to create Sonarr tag")
    except Exception as e:
        logger.error(f"Error creating Sonarr tag: {str(e)}")
    return None

def load_config():
    config_path = os.getenv('CONFIG_PATH', '/app/config/config.json')
    try:
        with open(config_path, 'r') as file:
            config = json.load(file)
        if 'rules' not in config:
            config['rules'] = {}
        if 'default_rule' not in config:
            config['default_rule'] = '1n1'
        return config
    except FileNotFoundError:
        return {
            'rules': {
                '1n1': {
                    'get_option': '1',
                    'action_option': 'search',
                    'keep_watched': '1',
                    'monitor_watched': False,
                    'series': []
                }
            },
            'default_rule': '1n1'
        }

def sync_rules_to_sonarr_tags():
    """Ensure all rules have corresponding tags in Sonarr."""
    config = load_config()
    existing_tags = get_tag_mapping()
    existing_tag_names = {tag_name.lower() for tag_name in existing_tags.values()}
    
    for rule_name in config['rules'].keys():
        if rule_name.lower() not in existing_tag_names:
            logger.info(f"Creating missing tag for rule: {rule_name}")
            create_tag_in_sonarr(rule_name)

def save_config(config):
    config_path = os.getenv('CONFIG_PATH', '/app/config/config.json')
    with open(config_path, 'w') as file:
        json.dump(config, file, indent=4)
    if not CLIENT_ONLY:
        sync_rules_to_sonarr_tags()

def get_missing_log_content():
    try:
        with open(MISSING_LOG_PATH, 'r') as file:
            return file.read()
    except FileNotFoundError:
        return "No missing entries logged."
    except Exception as e:
        logger.error(f"Failed to read missing log: {str(e)}")
        return "Failed to read log."

# Route handlers
@app.route('/webhook', methods=['POST'])
def handle_server_webhook():
    """Handle webhooks from Plex/Tautulli"""
    logger.info("Received webhook from Tautulli")
    data = request.json
    if data:
        try:
            temp_dir = '/app/temp'
            os.makedirs(temp_dir, exist_ok=True)
            with open(os.path.join(temp_dir, 'data_from_server.json'), 'w') as f:
                json.dump(data, f)
            
            result = subprocess.run(["python3", "/app/servertosonarr.py"], capture_output=True, text=True)
            if result.stderr:
                logger.error(f"Servertosonarr.py error: {result.stderr}")
            return jsonify({'status': 'success'}), 200
        except Exception as e:
            logger.error(f"Failed to process Tautulli webhook: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    return jsonify({'status': 'error', 'message': 'No data received'}), 400

@app.route('/jellyfin-webhook', methods=['POST'])
def handle_jellyfin_webhook():
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data received'}), 400

    try:
        if data.get('NotificationType') == 'PlaybackProgress':
            position_ticks = int(data.get('PlaybackPositionTicks', 0))
            total_ticks = int(data.get('RunTimeTicks', 0))
            
            if total_ticks > 0:
                progress_percent = (position_ticks / total_ticks) * 100
                
                if 45 <= progress_percent <= 55:
                    series_name = data.get('SeriesName')
                    season = data.get('SeasonNumber')
                    episode = data.get('EpisodeNumber')
                    logger.info(f"Processing Jellyfin progress: {series_name} S{season}E{episode}")
                    
                    episode_data = {
                        "server_title": series_name,
                        "server_season_num": str(season),
                        "server_ep_num": str(episode)
                    }
                    
                    temp_dir = '/app/temp'
                    os.makedirs(temp_dir, exist_ok=True)
                    with open(os.path.join(temp_dir, 'data_from_server.json'), 'w') as f:
                        json.dump(episode_data, f)
                    
                    result = subprocess.run(["python3", "/app/servertosonarr.py"],
                                       capture_output=True,
                                       text=True)
                    
                    if result.stderr:
                        logger.error(f"Servertosonarr.py error: {result.stderr}")
            
            return jsonify({'status': 'success'}), 200
            
    except Exception as e:
        logger.error(f"Failed to process Jellyfin webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/sonarr-webhook', methods=['POST'])
def handle_sonarr_webhook():
    """Handle webhooks from Sonarr for series additions."""
    data = request.json
    if not data:
        logger.warning("Empty webhook received from Sonarr")
        return jsonify({'status': 'error', 'message': 'No data received'}), 400

    try:
        if data.get('eventType') == 'SeriesAdd':
            series_id = data.get('series', {}).get('id')
            title = data.get('series', {}).get('title')
            tags = data.get('series', {}).get('tags', [])
            
            if series_id:
                logger.info(f"Processing new series: {title} (ID: {series_id}) with tags: {tags}")
                
                from servertosonarr import get_rule_by_tags, apply_rule_to_series
                rule = get_rule_by_tags(tags)
                apply_rule_to_series(series_id, rule)
                
                return jsonify({
                    'status': 'success', 
                    'message': 'Applied rule to new series'
                }), 200
               
        return jsonify({'status': 'success', 'message': 'Webhook processed'}), 200
       
    except Exception as e:
        logger.error(f"Error processing series addition: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/')
def home():
    preferences = sonarr_utils.load_preferences()
    current_series = sonarr_utils.fetch_series_and_episodes(preferences)
    upcoming_premieres = sonarr_utils.fetch_upcoming_premieres(preferences)
    use_posters = os.getenv('USE_POSTERS', 'false').lower() == 'true'

    if CLIENT_ONLY:
        return render_template('index.html',
                             current_series=current_series,
                             upcoming_premieres=upcoming_premieres,
                             use_posters=use_posters,
                             sonarr_url=SONARR_URL,
                             config={'CLIENT_ONLY': CLIENT_ONLY})

    # Full functionality for non-client mode
    config = load_config()
    all_series = sonarr_utils.get_series_list(preferences)
    rules_mapping = {str(series_id): rule_name for rule_name, details in config['rules'].items() 
                    for series_id in details.get('series', [])}
    
    default_rule = config.get('default_rule', '1n1')
    for series in all_series:
        series['assigned_rule'] = rules_mapping.get(str(series['id']), default_rule)

    missing_log_content = get_missing_log_content()
    rule = request.args.get('rule', '1n1')

    return render_template('index.html',
                         config=config,
                         current_series=current_series,
                         upcoming_premieres=upcoming_premieres,
                         all_series=all_series,
                         sonarr_url=SONARR_URL,
                         missing_log=missing_log_content,
                         rule=rule,
                         use_posters=use_posters)

@app.route('/update-settings', methods=['POST'])
def update_settings():
    if CLIENT_ONLY:
        return jsonify({'status': 'error', 'message': 'Settings disabled in client mode'}), 400
        
    try:
        config = load_config()
        rule_name = request.form.get('rule_name')
        if rule_name == 'add_new':
            rule_name = request.form.get('new_rule_name')
            if not rule_name:
                return redirect(url_for('home', section='settings', message="New rule name required"))

        logger.info(f"Updating settings for rule: {rule_name}")
        config['rules'][rule_name] = {
            'get_option': request.form.get('get_option'),
            'action_option': request.form.get('action_option'),
            'keep_watched': request.form.get('keep_watched'),
            'monitor_watched': request.form.get('monitor_watched', 'false').lower() == 'true',
            'series': config['rules'].get(rule_name, {}).get('series', [])
        }

        if request.form.get('default_rule'):
            config['default_rule'] = rule_name

        save_config(config)
        return redirect(url_for('home', section='settings', message="Settings updated"))
    except Exception as e:
        logger.error(f"Failed to update settings: {str(e)}")
        return redirect(url_for('home', section='settings', message="Error updating settings"))

@app.route('/delete_rule', methods=['POST'])
def delete_rule():
    if CLIENT_ONLY:
        return jsonify({'status': 'error', 'message': 'Rule deletion disabled in client mode'}), 400
        
    config = load_config()
    rule_name = request.form.get('rule_name')
    if rule_name and rule_name in config['rules']:
        logger.info(f"Deleting rule: {rule_name}")
        del config['rules'][rule_name]
        save_config(config)
        return redirect(url_for('home', section='settings', message=f"Rule '{rule_name}' deleted"))
    return redirect(url_for('home', section='settings', message=f"Rule not found"))

@app.route('/assign_rules', methods=['POST'])
def assign_rules():
    if CLIENT_ONLY:
        return jsonify({'status': 'error', 'message': 'Rule assignment disabled in client mode'}), 400
        
    config = load_config()
    rule_name = request.form.get('assign_rule_name')
    submitted_series_ids = set(request.form.getlist('series_ids'))

    logger.info(f"Assigning rule '{rule_name}' to series IDs: {submitted_series_ids}")

    if not rule_name or rule_name == 'remove':
        for key, details in config['rules'].items():
            details['series'] = [sid for sid in details.get('series', []) if sid not in submitted_series_ids]
    else:
        if rule_name in config['rules']:
            current_series = set(config['rules'][rule_name]['series'])
            updated_series = current_series.union(submitted_series_ids)
            config['rules'][rule_name]['series'] = list(updated_series)

        for key, details in config['rules'].items():
            if key != rule_name:
                details['series'] = [sid for sid in details.get('series', []) if sid not in submitted_series_ids]

    save_config(config)
    return redirect(url_for('home', section='settings', message="Rules updated"))

if not CLIENT_ONLY:
    sync_rules_to_sonarr_tags()

if __name__ == '__main__':
    logger.info("Starting OCDarr webhook listener")
    app.run(host='0.0.0.0', port=5001, debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')