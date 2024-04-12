from flask import Flask, render_template, request, redirect, url_for
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
            'get_option': 'episode',
            'action_option': 'search',
            'already_watched': 'keep',
            'always_keep': [],
            'watched_percent': 90 #does not work at this point
        }
        save_config(default_config)
        return default_config

def normalize_name(name):
    return ' '.join(word.capitalize() for word in name.replace('_', ' ').split())

def save_config(config):
    with open(config_path, 'w') as file:
        json.dump(config, file, indent=4)

@app.route('/')
def home():
    config = load_config()
    preferences = sonarr_utils.load_preferences()
    current_series = sonarr_utils.fetch_series_and_episodes(preferences)
    upcoming_premieres = sonarr_utils.fetch_upcoming_premieres(preferences)
    return render_template('index.html', config=config, current_series=current_series, upcoming_premieres=upcoming_premieres)

@app.route('/settings')
def settings():
    config = load_config()
    message = request.args.get('message', '')
    return render_template('settings.html', config=config, message=message)

@app.route('/update-settings', methods=['POST'])
def update_settings():
    config = load_config()
    config['get_option'] = request.form.get('get_option', config['get_option'])
    config['action_option'] = request.form.get('action_option', config['action_option'])
    config['already_watched'] = request.form.get('already_watched', config['already_watched'])
    config['always_keep'] = [normalize_name(name.strip()) for name in request.form.get('always_keep', '').split(',')]
    config['watched_percent'] = int(request.form.get('watched_percent', config['watched_percent'])) #does not work at this point
    save_config(config)
    # Redirect back to the settings section with a success message
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return redirect(url_for('home', section='settings', message=f"Settings updated successfully on {current_time}"))

@app.route('/webhook', methods=['POST'])
def handle_server_webhook():
    app.logger.info("Received POST request from Server")
    try:
        result = subprocess.run(["python3", "/app/servertosonarr.py"], capture_output=True, text=True)
        app.logger.info("Successfully ran servertosonarr.py: " + result.stdout)
        if result.stderr:
            app.logger.error("Errors from servertosonarr.py: " + result.stderr)
    except subprocess.CalledProcessError as e:
        app.logger.error(f"Failed to run servertosonarr.py: {e}")
    return 'Success', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')