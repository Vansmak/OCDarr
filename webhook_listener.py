import logging
from flask import Flask, render_template, request
import sonarr_utils
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, filename='/home/pi/tidiarr/app.log', filemode='a',
                    format='%(name)s - %(levelname)s - %(message)s')

app = Flask(__name__)

@app.route('/')
def home():
    preferences = sonarr_utils.load_preferences()  # Make sure to load preferences
    series_data = sonarr_utils.fetch_series_and_episodes(preferences)
    return render_template('index.html', series_data=series_data)

@app.route('/webhook', methods=['POST'])
def handle_plex_webhook():
    logging.info("Received POST request from Plex")
    # Log the request data if needed
    # logging.info(request.json)

    try:
        subprocess.run(["/usr/bin/python3", "/home/pi/tidiarr/plextosonarr.py"], capture_output=True, text=True)
        logging.info("Successfully ran plextosonarr.py")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to run plextosonarr.py: {e}")
    
    return 'Success', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


