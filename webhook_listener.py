from flask import Flask, request
import subprocess

app = Flask(__name__)

@app.route('/plex_watched', methods=['POST'])
def handle_plex_webhook():
    if request.method == 'POST':
        # Assuming the main functionality of your script is in a function called `main` within `next_episode.py`
        # Trigger your script or the specific function you need
        subprocess.run(["python3", "next_episode.py"])
        return 'Success', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
