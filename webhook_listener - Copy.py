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
            return json.load(file)
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
                    "monitor_watched": False
                }
            }
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

@app.route('/')
def home():
    config = load_config()
    preferences = sonarr_utils.load_preferences()
    current_series = sonarr_utils.fetch_series_and_episodes(preferences)
    upcoming_premieres = sonarr_utils.fetch_upcoming_premieres(preferences)
    missing_log_content = get_missing_log_content()  # Fetch the missing log content here
    return render_template('index.html', config=config, current_series=current_series, upcoming_premieres=upcoming_premieres, sonarr_url=SONARR_URL, missing_log=missing_log_content)

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
        'monitor_watched': request.form.get('monitor_watched', 'false').lower() == 'true'
    }
    
    save_config(config)
    return redirect(url_for('home', section='settings', message="Settings updated successfully"))

@app.route('/delete_rule', methods=['POST'])
def delete_rule():
    config = load_config()
    rule_name = request.form.get('rule_name')
    if rule_name and rule_name in config['rules']:
        if rule_name == 'default':
            return redirect(url_for('home', section='settings', message="Default rule cannot be deleted."))
        del config['rules'][rule_name]
        save_config(config)
        return redirect(url_for('home', section='settings', message=f"Rule '{rule_name}' deleted successfully."))
    else:
        return redirect(url_for('home', section='settings', message=f"Rule '{rule_name}' not found."))



@app.route('/webhook', methods=['POST'])
def handle_server_webhook():
    app.logger.info("Received POST request from Tautulli")
    data = request.json
    if data:
        app.logger.info(f"Webhook received with data: {data}")
        try:
            temp_dir = '/app/temp'
            os.makedirs(temp_dir, exist_ok=True)  # Ensure the temp directory exists
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
