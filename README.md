# Overview

I created a script to integrate with plex (jellyfin) and sonarr to automate tv show maintenance.  I am my only user so I like things to be tidy, as a watch a series this will always have the next episode ready and clean the previous ones.  If one prefers to keep episodes you can, if one prefers to get the full season you can. I use a plex webhook to trigger the script so anytime there is an active session in plex the script goes to work based on your preferences.  For example, my prefernces is if im watching breaking bad season 3 episode 3 then my script will unmonitor this episode and delete the one before it s3ep2, then monitor and search for season 3 episode 4 so it will be on deck. This way I always have the one I watched and the next one.  I also like a visual and feel many apps like trakt, tvtime etc are too busy. I like a basic look of whats next so included is an html using another script that I embed on my homarr page it shows me the latest episodes to watch and season or series premiering soon. 
## Features
- Automatically triggers searches for the next episode in Sonarr based on your viewing progress.
- Manages older episodes by optionally unmonitoring and deleting them to save space.
- Provides flexibility to choose between episode-based or season-based actions.
- Integrates with Plex webhooks for seamless operation during active sessions.
- Optional HTML
- works with plex, jellyfin needs to be tested
  ![watching](https://github.com/Vansmak/tidiarr/assets/16037573/068af13e-de0a-4b65-848e-bb709eb27a1d) ![premiering](https://github.com/Vansmak/tidiarr/assets/16037573/80483a6a-22f5-424d-8bd5-3586d2224d5d)


## Server-Sonarr Episode Trigger  
This script is designed to automate the process of triggering a search for the next episode(s) and optionally delete of a TV series in Sonarr when the current episode is being played in Plex. It's particularly useful for managing older shows where you don't want to download entire seasons upfront, thus saving space and ensuring a seamless viewing experience.

## Installation

### Clone the Repository
Clone the repository to your local machine:
```
git clone https://github.com/Vansmak/tidiarr.git

```
### Install Dependencies \ optional
Navigate to the cloned repository directory and install the required Python packages:

```
pip install requests Flask
```

## Configuration

### Setup Configuration File
1. **Copy the Example Configuration**: Start by copying `preferences.example.json` to `preferences.json` in the same directory.
2. **Fill in Your Details**: Replace `YOUR_PLEX_OR_JF_TOKEN_HERE`, `YOUR_SONARR_API_KEY_HERE`, and other placeholder values with your actual configuration details.

### Understanding Options
- `server_type`: Plex or Jellyfin
- `get_option`: Determines the scope of the action. Options are 'episode' for targeting the next unwatched episode, and 'season' for targeting all remaining episodes in the current season.
- `action_option`: Specifies the action the script should take regarding the episodes. 'search' triggers a search for the episode(s) in Sonarr. 'monitor' sets Sonarr to monitor the episode(s) without serching.
- `watched_percent`: What percent of the episode should be played. Enter any #.
- `already_watched`: New option that determines how the script handles episodes that have already been watched. 'keep' will retain all previously watched episodes, while 'delete' will remove episodes all but last
### Save the File
After making your changes, save the file as `preferences.json`.

## Usage

### Manual Execution
You can manually execute the script from the command line:
```
python3 servertosonarr.py

```
Note: This script is meant to be automatic and will not do anything unless there is a Plex session.

### Automation with Cron Job
To automate the script using cron jobs, edit your crontab:
Then add the following line to run the script every 5 minutes:
```
crontab -e
*/5 * * * * /usr/bin/python3 /path/to/servertosonarr.py

```

### Flask Webhooks
Preferably, you can set up a Flask server with a webhook endpoint that triggers the script. This allows for integration with various services like Plex webhooks.

#### Install Flask
If not already installed during the dependency installation step:
```
pip install Flask
```

#### Configure Plex Webhook
In your Plex server settings, set up a webhook pointing to the Flask endpoint. This will notify the script whenever a new episode starts playing.

Ensure to replace `/path/to/servertosonarr.py` with the actual path where your `plextosonarr.py` script is located on your system.

#### Sonarr Utils HTML Serving (Optional)
If you prefer, you can use Sonarr Utils to serve HTML instead of Flask. This is useful if you already have a way to serve HTML or want to avoid using Flask.

### Removing Sonarr Utils HTML Serving (Optional)
If you prefer not to use Sonarr Utils for HTML serving, you can remove it from the webhook_listener code. Simply edit the `webhook_listener.py` file and remove the following lines:

```
import sonarr_utils
```
```
@app.route('/')
def home():
    preferences = sonarr_utils.load_preferences()
    series_data = sonarr_utils.fetch_series_and_episodes(preferences)
    return render_template('index.html', series_data=series_data)
```
