import logging
from flask import Flask, render_template, request
import sonarr_utils  # Assuming fetch_series_and_episodes and fetch_upcoming_premieres are defined here
import subprocess
import os

# Configure logging
log_file_path = os.getenv('LOG_PATH', '/app/logs/app.log')
logging.basicConfig(level=logging.INFO, filename=log_file_path, filemode='a',
                    format='%(name%s - %(levelname)s - %(message)s')

app = Flask(__name__)

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
    logging.info("Received POST request from Server")
    try:
        # Ensuring the command runs in the expected environment
        subprocess.run(["/usr/bin/python3", "/home/pi/OCDarr/servertosonarr.py"], capture_output=True, text=True)
        logging.info("Successfully ran servertosonarr.py")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to run servertosonarr.py: {e}")
    return 'Success', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')




