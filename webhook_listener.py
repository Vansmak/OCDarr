import os
import requests
import logging
import json
import subprocess
from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
from dotenv import load_dotenv
import sonarr_utils

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Load environment variables
SONARR_URL = os.getenv('SONARR_URL')
SONARR_API_KEY = os.getenv('SONARR_API_KEY')
MISSING_LOG_PATH = os.getenv('MISSING_LOG_PATH', '/app/logs/missing.log')

# Setup logging to capture all logs
logging.basicConfig(filename=os.getenv('LOG_PATH', '/app/logs/app.log'), 
                    level=logging.DEBUG if os.getenv('FLASK_DEBUG', 'false').lower() == 'true' else logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Adding stream handler to also log to console for Docker logs to capture
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG if os.getenv('FLASK_DEBUG', 'false').lower() == 'true' else logging.INFO)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
stream_handler.setFormatter(formatter)
app.logger.addHandler(stream_handler)

# Configuration management
config_path = os.path.join(app.root_path, 'config', 'config.json')

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
                    "monitor_watched": False,
                    "series": []
                }
            }
        if 'rules_mapping' not in config:
            config['rules_mapping'] = {}
        return config
    except FileNotFoundError:
        default_config = {
            'get_option': "sonarr",
            'action_option': "sonarr",
            'keep_watched': "sonarr",
            'monitor_watched': False,
            'rules': {
                "default": {
                    "get_option": "sonarr",
                    "action_option": "sonarr",
                    "keep_watched": "sonarr",
                    "monitor_watched": False,
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

def normalize_name(name):
    return ' '.join(word.capitalize() for word in name.replace('_', ' ').split())

def get_missing_log_content():
    try:
        with open(MISSING_LOG_PATH, 'r') as file:
            return file.read()
    except FileNotFoundError:
        return "No missing entries logged."
    except Exception as e:
        app.logger.error(f"Failed to read missing log: {str(e)}")
        return "Failed to read log."

def get_all_series():
    url = f"{SONARR_URL}/api/v3/series"
    headers = {'X-Api-Key': SONARR_API_KEY}
    response = requests.get(url, headers=headers)
    return response.json() if response.ok else []

@app.route('/')
def home():
    config = load_config()
    preferences = sonarr_utils.load_preferences()
    current_series = sonarr_utils.fetch_series_and_episodes(preferences)
    upcoming_premieres = sonarr_utils.fetch_upcoming_premieres(preferences)
    missing_log_content = get_missing_log_content()
    all_series = get_all_series()
    return render_template('index.html', config=config, current_series=current_series, upcoming_premieres=upcoming_premieres, all_series=all_series, sonarr_url=SONARR_URL, missing_log=missing_log_content)

@app.route('/settings')
def settings():
    config = load_config()
    missing_log_content = get_missing_log_content()
    message = request.args.get('message', '')

    app.logger.debug(f"Missing Log Content: {missing_log_content}")
    show_settings = request.args.get('show_settings', 'false').lower() == 'true'
    
    return render_template('index.html', 
                           config=config, 
                           message=message, 
                           missing_log=missing_log_content, 
                           sonarr_url=SONARR_URL, 
                           show_settings=show_settings)

@app.route('/update-settings', methods=['POST'])
def update_settings():
    config = load_config()
    
    rule_name = request.form.get('rule_name')
    if rule_name == 'add_new':
        rule_name = request.form.get('new_rule_name')
        if not rule_name:
            return redirect(url_for('settings', message="New rule name is required."))
    
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
    return redirect(url_for('settings', show_settings='true', message="Settings updated successfully"))

@app.route('/delete_rule', methods=['POST'])
def delete_rule():
    config = load_config()
    rule_name = request.form.get('rule_name')
    if rule_name in config['rules']:
        del config['rules'][rule_name]
        save_config(config)
        return redirect(url_for('settings', show_settings='true', message=f"Rule '{rule_name}' deleted successfully."))
    else:
        return redirect(url_for('settings', show_settings='true', message=f"Rule '{rule_name}' not found."))

@app.route('/assign_rules', methods=['POST'])
def assign_rules():
    config = load_config()
    rule_name = request.form.get('assign_rule_name')
    series_ids = request.form.getlist('series_ids')
    
    if rule_name and series_ids:
        for rule in config['rules'].values():
            rule['series'] = [series_id for series_id in rule.get('series', []) if series_id not in series_ids]

        if rule_name in config['rules']:
            config['rules'][rule_name]['series'].extend(series_ids)
            config['rules'][rule_name]['series'] = list(set(config['rules'][rule_name]['series']))
        
        save_config(config)
        return redirect(url_for('settings', show_settings='true', message="Rules assigned to selected series."))
    return redirect(url_for('settings', show_settings='true', message="Failed to assign rules to selected series."))

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
