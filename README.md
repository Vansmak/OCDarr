# Plex-Sonarr Episode Trigger

## Overview
This script is designed to automate the process of triggering a search for the next episode(s) and optionally delete of a TV series in Sonarr when the current episode is being played in Plex. It's particularly useful for managing older shows where you don't want to download entire seasons upfront, thus saving space and ensuring a seamless viewing experience.

## Installation

### Clone the Repository
Clone the repository to your local machine:
```
git clone https://github.com/Vansmak/plextosonarr.git

```
### Install Dependencies \ optional
Navigate to the cloned repository directory and install the required Python packages:

```
pip install requests Flask
```

## Configuration

### Setup Configuration File
1. **Copy the Example Configuration**: Start by copying `preferences.example.json` to `preferences.json` in the same directory.
2. **Fill in Your Details**: Replace `YOUR_PLEX_TOKEN_HERE`, `YOUR_SONARR_API_KEY_HERE`, and other placeholder values with your actual configuration details.

### Understanding Options
- `get_option`: Determines the scope of the action. Options are 'episode' for targeting the next unwatched episode, and 'season' for targeting all remaining episodes in the current season.
- `action_option`: Specifies the action the script should take regarding the episodes. 'search' triggers a search for the episode(s) in Sonarr. 'monitor' sets Sonarr to monitor the episode(s) without initiating a search.
- `watched_percent`: What percent of the episode should be played. Enter any #.
- `already_watched`: New option that determines how the script handles episodes that have already been watched. 'keep' will retain all previously watched episodes, while 'delete' will remove episodes more than one step back from the currently watched episode, keeping the collection tidy and saving space.
### Save the File
After making your changes and removing the pseudo-comments, save the file as `preferences.json`.

## Usage

### Manual Execution
You can manually execute the script from the command line:
```
python3 plextosonarr.py

```
Note: This script is meant to be automatic and will not do anything unless there is a Plex session.

### Automation with Cron Job
To automate the script using cron jobs, edit your crontab:
Then add the following line to run the script every 5 minutes:
```
crontab -e
*/5 * * * * /usr/bin/python3 /path/to/plextosonarr.py

```

### Flask Webhooks
Alternatively, you can set up a Flask server with a webhook endpoint that triggers the script. This allows for integration with various services like Plex webhooks.

#### Install Flask
If not already installed during the dependency installation step:
```
pip install Flask
```

#### Configure Plex Webhook
In your Plex server settings, set up a webhook pointing to the Flask endpoint. This will notify the script whenever a new episode starts playing.

Ensure to replace `/path/to/plextosonarr.py` with the actual path where your `plextosonarr.py` script is located on your system.


