from flask import Flask, render_template, request
import subprocess
import os
import logging
import sonarr_utils
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Setup logging to output to gunicorn's stderr
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG if os.getenv('FLASK_DEBUG', 'false').lower() == 'true' else logging.INFO)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
stream_handler.setFormatter(formatter)
app.logger.addHandler(stream_handler)
app.logger.setLevel(stream_handler.level)

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
        # Adjusted for typical Docker Python location and script path
        result = subprocess.run(["python3", "/app/servertosonarr.py"], capture_output=True, text=True)
        app.logger.info("Successfully ran servertosonarr.py: " + result.stdout)
        if result.stderr:
            app.logger.error("Errors from servertosonarr.py: " + result.stderr)
    except subprocess.CalledProcessError as e:
        app.logger.error(f"Failed to run servertosonarr.py: {e}")
    return 'Success', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')

