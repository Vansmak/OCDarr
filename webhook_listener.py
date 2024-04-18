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
            'always_keep': []
            
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
    
    # Update the configuration with form data
    get_option = request.form.get('get_option')
    if get_option.isdigit():  # If it's a number, convert to int
        config['get_option'] = int(get_option)
    else:
        config['get_option'] = get_option  # Otherwise, save as string

    action_option = request.form.get('action_option')
    config['action_option'] = action_option

    already_watched = request.form.get('already_watched')
    if already_watched.isdigit():  # Handling numbers for episodes to keep
        config['already_watched'] = int(already_watched)
    else:
        config['already_watched'] = already_watched

    always_keep = request.form.get('always_keep', '').split(',')
    config['always_keep'] = [normalize_name(name.strip()) for name in always_keep if name.strip()]  # Normalize and save

    

    save_config(config)  # Save the updated configuration

    # Redirect back to the settings section with a success message
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return redirect(url_for('home', section='settings', message=f"Settings updated successfully on {current_time}"))



@app.route('/webhook', methods=['POST'])
def handle_server_webhook():
    app.logger.info("Received POST request from Tautulli")
    data = request.json  # Assuming data is properly formatted JSON from Tautulli

    if data:
        app.logger.info(f"Webhook received with data: {data}")
        try:
            # Write the received data to a temporary file
            with open('/app/temp/data_from_tautulli.json', 'w') as f:
                json.dump(data, f)
            app.logger.info("Data successfully written to data_from_tautulli.json")

            # Trigger the script processing
            result = subprocess.run(["python3", "/app/servertosonarr.py"], capture_output=True, text=True)
            app.logger.info("Successfully ran servertosonarr.py: " + result.stdout)
            if result.stderr:
                app.logger.error("Errors from servertosonarr.py: " + result.stderr)
        except Exception as e:
            app.logger.error(f"Failed to handle data or run script: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
        return jsonify({'status': 'success', 'message': 'Script triggered successfully'}), 200
    else:
        app.logger.error("No data received from webhook")
        return jsonify({'status': 'error', 'message': 'No data received'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')