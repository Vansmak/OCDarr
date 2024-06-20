import os
import requests
import logging
import json
from flask import Flask, render_template, request, redirect, url_for, jsonify
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Load environment variables
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

# Configuration management
config_path = os.getenv('CONFIG_PATH', '/app/config/config.json')

def load_config():
    try:
        with open(config_path, 'r') as file:
            config = json.load(file)
        if 'rules' not in config:
            config['rules'] = {
                "default": {
                    "get_option": "sonarr",
                    "action_option": "sonarr",
                    "keep_watched": "sonarr",
                    "monitor_watched": "sonarr",
                    "series": []
                }
            }
        return config
    except FileNotFoundError:
        default_config = {
            'get_option': "sonarr",
            'action_option': "sonarr",
            'keep_watched': "sonarr",
            'monitor_watched': "sonarr",
            'rules': {
                "default": {
                    "get_option": "sonarr",
                    "action_option": "sonarr",
                    "keep_watched": "sonarr",
                    "monitor_watched": "sonarr",
                    "series": []
                }
            },
            'rules_mapping': {}
        }
        save_config(default_config)
        return default_config

def save_config(config):
    with open(config_path, 'w') as file:
        json.dump(config, file, indent=4)

@app.route('/')
def home():
    config = load_config()
    preferences = sonarr_utils.load_preferences()
    current_series = sonarr_utils.fetch_series_and_episodes(preferences)
    upcoming_premieres = sonarr_utils.fetch_upcoming_premieres(preferences)
    all_series = sonarr_utils.get_series_list(preferences)
    
    # Build a dictionary that maps series IDs to their assigned rules
    rules_mapping = {str(series_id): rule_name for rule_name, details in config['rules'].items() for series_id in details.get('series', [])}

    # Annotate each series with its assigned rule or 'None'
    for series in all_series:
        series['assigned_rule'] = rules_mapping.get(str(series['id']), 'None')

    missing_log_content = get_missing_log_content()

    return render_template('index.html', config=config, current_series=current_series, 
                           upcoming_premieres=upcoming_premieres, all_series=all_series, 
                           sonarr_url=SONARR_URL, missing_log=missing_log_content)

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
    monitor_watched = request.form.get('monitor_watched')

    config['rules'][rule_name] = {
        'get_option': get_option,
        'action_option': request.form.get('action_option'),
        'keep_watched': keep_watched,
        'monitor_watched': monitor_watched,
        'series': config['rules'].get(rule_name, {}).get('series', [])
    }
    
    save_config(config)
    return redirect(url_for('home', section='settings', message="Settings updated successfully"))

@app.route('/delete_rule', methods=['POST'])
def delete_rule():
    config = load_config()
    rule_name = request.form.get('rule_name')
    if rule_name in config['rules']:
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

    # Update the rule's series list to include only those submitted
    if rule_name in config['rules']:
        config['rules'][rule_name]['series'] = [sid for sid in submitted_series_ids]

    # Update other rules to remove the series if it's no longer assigned there
    for key, details in config['rules'].items():
        if key != rule_name:
            details['series'] = [sid for sid in details.get('series', []) if sid not in submitted_series_ids]

    save_config(config)
    return redirect(url_for('home', section='assign_rules', rule=rule_name, message="Rules updated successfully."))

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')
