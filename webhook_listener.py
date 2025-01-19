from flask import Flask, render_template, request, redirect, url_for, jsonify
import subprocess
import os
import logging
import json
import sonarr_utils
from datetime import datetime
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Load environment variables
SONARR_URL = os.getenv('SONARR_URL')
SONARR_API_KEY = os.getenv('SONARR_API_KEY')
MISSING_LOG_PATH = os.getenv('MISSING_LOG_PATH', '/app/logs/missing.log')
CLIENT_ONLY = os.getenv('CLIENT_ONLY', 'false').lower() == 'true'

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

def load_config():
    config_path = os.getenv('CONFIG_PATH', '/app/config/config.json')
    try:
        with open(config_path, 'r') as file:
            config = json.load(file)
        if 'rules' not in config:
            config['rules'] = {}

        if 'default_rule' not in config:
            config['default_rule'] = 'default'
            if 'default' not in config['rules']:
                config['rules']['default'] = {
                    'get_option': 'season',
                    'action_option': 'monitor',
                    'keep_watched': 'season',
                    'monitor_watched': True,
                    'series': []
                }
        return config
    except FileNotFoundError:
        return {
            'rules': {
                'default': {
                    'get_option': 'season',
                    'action_option': 'monitor',
                    'keep_watched': 'season',
                    'monitor_watched': True,
                    'series': []
                }
            },
            'default_rule': 'default'
        }

def save_config(config):
    config_path = os.getenv('CONFIG_PATH', '/app/config/config.json')
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
    
    default_rule = config.get('default_rule', 'default')
    for series in all_series:
        series['assigned_rule'] = rules_mapping.get(str(series['id']), default_rule)

    missing_log_content = get_missing_log_content()
    rule = request.args.get('rule', 'full_seasons')

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
        
    config = load_config()
    rule_name = request.form.get('rule_name')
    if rule_name == 'add_new':
        rule_name = request.form.get('new_rule_name')
        if not rule_name:
            return redirect(url_for('home', section='settings', message="New rule name is required."))

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
    return redirect(url_for('home', section='settings', message="Settings updated successfully"))

@app.route('/delete_rule', methods=['POST'])
def delete_rule():
    if CLIENT_ONLY:
        return jsonify({'status': 'error', 'message': 'Rule deletion disabled in client mode'}), 400
        
    config = load_config()
    rule_name = request.form.get('rule_name')
    if rule_name and rule_name in config['rules']:
        del config['rules'][rule_name]
        save_config(config)
        return redirect(url_for('home', section='settings', message=f"Rule '{rule_name}' deleted successfully."))
    return redirect(url_for('home', section='settings', message=f"Rule '{rule_name}' not found."))

@app.route('/assign_rules', methods=['POST'])
def assign_rules():
    if CLIENT_ONLY:
        return jsonify({'status': 'error', 'message': 'Rule assignment disabled in client mode'}), 400
        
    config = load_config()
    rule_name = request.form.get('assign_rule_name')
    submitted_series_ids = set(request.form.getlist('series_ids'))

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
    return redirect(url_for('home', section='settings', message="Rules updated successfully."))

@app.route('/webhook', methods=['POST'])
def handle_server_webhook():
    if CLIENT_ONLY:
        return jsonify({'status': 'success', 'message': 'Client only mode - no actions taken'}), 200
        
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
