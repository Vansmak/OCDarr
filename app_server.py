from flask import Flask, render_template, request, redirect, url_for
import subprocess
import os
import logging
import json
import sonarr_utils
from datetime import datetime
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(filename=os.getenv('LOG_PATH', '/app/logs/app.log'), 
                    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
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
    return render_template('index.html', config=config, current_series=current_series, upcoming_premieres=upcoming_premieres)

@app.route('/settings')
def settings():
    config = load_config()
    message = request.args.get('message', '')
    return render_template('settings.html', config=config, message=message)

@app.route('/update-settings', methods=['POST'])
def update_settings():
    config = load_config()
    config.update({
        'get_option': request.form.get('get_option', config['get_option']),
        'action_option': request.form.get('action_option', config['action_option']),
        'already_watched': request.form.get('already_watched', config['already_watched']),
        'always_keep': [name.strip().capitalize() for name in request.form.get('always_keep', '').split(',')]
    })
    save_config(config)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return redirect(url_for('home', section='settings', message=f"Settings updated successfully on {current_time}"))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')
