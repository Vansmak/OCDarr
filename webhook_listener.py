from flask import Flask, render_template, request, redirect, url_for, jsonify
import subprocess
import os
import logging
import json
import sonarr_utils
from datetime import datetime
from dotenv import load_dotenv
import sys

app = Flask(__name__)

# Define the format for logging
log_format = '%(asctime)s - %(levelname)s - %(message)s'

# Setup logging to avoid duplicate entries
for handler in app.logger.handlers:
    app.logger.removeHandler(handler)

file_handler = logging.FileHandler(os.getenv('LOG_PATH', '/app/logs/app.log'))
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(log_format))
app.logger.addHandler(file_handler)

if os.getenv('FLASK_DEBUG', 'false').lower() == 'true':
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(log_format))
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)
else:
    app.logger.setLevel(logging.INFO)

# Stop Flask's logger from handling the same logs
app.logger.propagate = False

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
    app.logger.debug("Loading the home page")
    config = load_config()
    preferences = sonarr_utils.load_preferences()
    current_series = upcoming_premieres = prime_series = None

    try:
        current_series = sonarr_utils.fetch_series_and_episodes(preferences)
    except Exception as e:
        app.logger.error(f"Failed to fetch current series: {e}")
        current_series = None

    try:
        upcoming_premieres = sonarr_utils.fetch_upcoming_premieres(preferences)
    except Exception as e:
        app.logger.error(f"Failed to fetch upcoming premieres: {e}")
        upcoming_premieres = None

    try:
        prime_series = sonarr_utils.fetch_tagged_series_names(preferences, 2)  # Ensure tag_id is an integer
    except Exception as e:
        app.logger.error(f"Failed to fetch prime series: {e}")
        prime_series = None

    return render_template('index.html', config=config, current_series=current_series, 
                           upcoming_premieres=upcoming_premieres, prime_series=prime_series)


@app.route('/settings')
def settings():
    config = load_config()
    message = request.args.get('message', '')
    sonarr_url = os.getenv('SONARR_URL') + '/add/new' 
    return render_template('settings.html', config=config, message=message, sonarr_url=sonarr_url)



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

@app.route('/logs')
def show_logs():
    log_type = request.args.get('type', 'app')  # Default to 'app', could also be 'error'

    # Define log file paths
    log_paths = {
        'app': '/app/logs/app.log',
        'error': '/app/logs/app.error.log'
    }
    log_path = log_paths.get(log_type, log_paths['app'])  # Fallback to app.log if type is unknown

    # Try to read the log file
    try:
        with open(log_path, 'r') as file:
            logs = file.read()
    except FileNotFoundError:
        logs = "Log file not found."

    return jsonify(logs=logs)

@app.route('/trigger-wake', methods=['POST'])
def trigger_wake():
    webhook_url = "http://192.168.254.64:8123/api/webhook/wakeoffice"
    try:
        response = requests.post(webhook_url)  # POST request to the webhook URL
        if response.status_code == 200:
            return jsonify({'status': 'success', 'message': 'Webhook triggered successfully'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Webhook failed with status code: ' + str(response.status_code)}), 500
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Failed to send webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/webhook', methods=['POST'])
def handle_server_webhook():
    data = request.json  # Assuming data is properly formatted JSON from Tautulli
    if not data:
        app.logger.error("No data received from webhook")
        return jsonify({'status': 'error', 'message': 'No data received'}), 400

    try:
        # Write the received data to a temporary file
        with open('/app/temp/data_from_tautulli.json', 'w') as f:
            json.dump(data, f)

        # Trigger the script processing
        result = subprocess.run(["python3", "/app/servertosonarr.py"], capture_output=True, text=True)
        if result.stderr:
            app.logger.error("Errors from servertosonarr.py: " + result.stderr)
            return jsonify({'status': 'error', 'message': 'Script execution failed'}), 500
        
        return jsonify({'status': 'success', 'message': 'Script triggered successfully'}), 200
    except Exception as e:
        app.logger.error(f"Failed to handle data or run script: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')
