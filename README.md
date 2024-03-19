Plex-Sonarr Episode Trigger

This script is designed to automatically trigger a search for the next episode of a TV series in Sonarr when the current episode is being played in Plex. It helps automate the process of downloading the next episode, ensuring a seamless viewing experience. For example, I don't always watch every episode or finish a season and don't want a bunch of episode taking up space. This works best for older aired shows. I add to plex watch list and have sonarr import list with plex tag the tell sonarr to only monitor the pilot episode. Now as I watch it it will tee up the next episode.  
Future versions:
 - download the remainder of the         season
 - only download of current episode      was watched for a certain %

Installation:
    Clone the repository to your local machine:

    bash
    git clone https://github.com/Vansmak/plextosonarr.git

    Install the required dependencies:

    bash
    pip install requests

Configuration

Before running the script, you need to configure the following variables in the script:

    PLEX_URL: The URL of your Plex server.
    PLEX_TOKEN: Your Plex authentication token.
    SONARR_BASE_URL: The base URL of your Sonarr server.
    SONARR_API_KEY: Your Sonarr API key.

Usage
Manual Execution

You can manually execute the script from the command line:

bash
python3 next_episode.py
(but this is meant to be automatic and will not do anything unless there is a plex session.) 

Automation
Cron Job

To automate the script using cron jobs, edit your crontab:

bash
crontab -e

Then add the following line to run the script every 5 minutes:

bash
*/5 * * * * /usr/bin/python3 /path/to/next_episode.py

Flask Webhooks

Alternatively, you can set up a Flask server with a webhook endpoint that triggers the script. This allows integration with various services like Plex webhooks.

    Install Flask:

    bash
    pip install Flask

    Run the Flask server:

    bash
    python3 webhook_server.py

    Set up a webhook in your Plex server to send notifications to the Flask endpoint whenever a new episode starts playing.


