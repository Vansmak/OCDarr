from flask import Flask, render_template, request
import subprocess
import os
import sonarr_utils
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

LOG_PATH = os.getenv('LOG_PATH', '/app/logs/app.log')
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

@app.route('/')
def home():
    # Load preferences from sonarr_utils and fetch series and premieres data
    preferences = sonarr_utils.load_preferences()
    current_series = sonarr_utils.fetch_series_and_episodes(preferences)
    upcoming_premieres = sonarr_utils.fetch_upcoming_premieres(preferences)

    # Render the index.html with the fetched data
    return render_template('index.html', current_series=current_series, upcoming_premieres=upcoming_premieres)

@app.route('/webhook', methods=['POST'])
def handle_server_webhook():
    app.logger.info("Received POST request from Server")
    try:
        # Ensuring the command runs in the expected environment
        subprocess.run(["/usr/bin/python3", "/home/pi/OCDarr/servertosonarr.py"], capture_output=True, text=True)
        app.logger.info("Successfully ran servertosonarr.py")
    except subprocess.CalledProcessError as e:
        app.logger.error(f"Failed to run servertosonarr.py: {e}")
    return 'Success', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=FLASK_DEBUG)
