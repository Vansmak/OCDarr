# OCDarr

OCDarr automates TV show maintenance in Sonarr based on Plex viewing activity (Jellyfin untested). It ensures that the next episode is ready and cleans up watched episodes based on user-defined preferences. Ideal for keeping your media server tidy and your series up-to-date without manual intervention. Not useful for hoarders.  Sometimes I start an old show and never finish, or takes awhile before I really get into it. So This way I dont have full seasons sitting there. I also do not have other users outside my household and am not a rewatcher of tv so I like to delete after a show is watched. This will always have the next episode ready to go and the last episode watched saved just in case.  If I need to protect a show because someone else is behind me then I can set certain shows to not delete.  If someone prefers getting full season instead of one episode you can do that. For example, if you have a new shows pilot episode only, once its watched the script can then monitor the rest of the season. Keep or delete previous episodes.  

## Features

- **Automatic Episode Management**: Triggers searches for the next episode or season in Sonarr based on viewing activity.
- **Space Management**: Optionally unmonitors and deletes watched episodes to save space.
- **Plex Integration**: Uses Plex webhooks to trigger actions automatically during viewing sessions.
- **User Interface**: Simple HTML interface for viewing upcoming episodes and premieres and updatting settings.
- **Dockerized**: Easy to deploy and manage as a Docker container.
- **Expandability**: Future features may include support for season packs and selective retention rules.

###Screen shots  

![html](https://github.com/Vansmak/OCDarr/assets/16037573/ad7fc551-c3de-452a-84f7-d5a7db4b938c)

## Installation

### Clone the Repository

Start by cloning the repository and navigating into the directory:

```
git clone https://github.com/Vansmak/OCDarr.git
cd OCDarr
```
Configuration
Environment Setup

Copy the provided .env.example to .env and update it with your Plex/Jellyfin and Sonarr details:

```

cp .env.example .env
nano .env  # use your preferred text editor
```
Fill in the environment variables:

  SERVER_URL: URL to your Plex/Jellyfin server.
  SERVER_TOKEN: Your Plex/Jellyfin API token.
  SONARR_URL: URL to your Sonarr server.
  SONARR_API_KEY: Your Sonarr API key.
  SERVER_TYPE: plex or jellyfin*

Docker Compose

Edit the docker-compose.yml file to suit your setup. Make sure the .env file is referenced correctly, and ports are mapped to your preference:



version: '3.8'
services:
  sonarr_script:
    build: .
    environment:
      - SERVER_TYPE=${SERVER_TYPE}
      - SERVER_URL=${SERVER_URL}
      - SERVER_TOKEN=${SERVER_TOKEN}
      - SONARR_URL=${SONARR_URL}
      - SONARR_API_KEY=${SONARR_API_KEY}
    env_file:
      - .env
    ports:
      - "5001:5001"
    volumes:
      - .:/app
      - ./logs:/app/logs
      - ./config:/app/config 
    restart: unless-stopped

Build and Run with Docker Compose

```

docker-compose up -d --build
```
This command builds the Docker image and runs it in detached mode.
Usage

Once your Docker container is running, it will listen for webhook calls from Plex when media is played. Configure your Plex server to send webhooks to http://<docker-host-ip>:5001/.
Config.json

Modify config.json to fine-tune behavior:

  get_option: episode for next episodes, season for full seasons.
  action_option: search to search episodes, monitor to only monitor.
  watched_percent: Percentage of an episode that must be watched to trigger actions. ###future enhancement, currently does not work
  already_watched: keep to retain watched episodes, delete to remove them.
  always_keep: show names to keep even if delete is set, comma seperated

Additional Notes

  The script currently has untested support for Jellyfin.
   
Troubleshooting

If you encounter issues, check the Docker container logs and logs/app.log and ensure all environment variables are correctly set.
