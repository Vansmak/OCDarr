# OCDarr (customized for personal use, not for public)

OCDarr automates TV show maintenance in Sonarr based on Plex viewing activity via Tautulli. It ensures that the next episode is ready and cleans up watched episodes based on user-defined preferences. Ideal for keeping your media server tidy and your series up-to-date without manual intervention. Not useful for hoarders.  Sometimes I start an old show and never finish, or takes awhile before I really get into it. So This way I dont have full seasons sitting there. I also do not have other users outside my household and am not a rewatcher of tv so I like to delete after a show is watched. This will always have the next episode ready to go and the last episode watched saved just in case.  If I need to protect a show because someone else is behind me then I can set certain shows to not delete.  If someone prefers getting full season instead of one episode you can do that. For example, if you have a new shows pilot episode only, once its watched the script can then monitor the rest of the season. Keep or delete previous episodes.  

## Features

- **Automatic Episode Management**: Triggers searches for the next episode(s) or season in Sonarr based on viewing activity.
- **Space Management**: Optionally unmonitors and deletes watched episodes to save space.
- **Plex\Tautulli Integration**: Uses Tautulli webhook notifications to trigger actions automatically when episode is watched.
- **User Interface**: Simple HTML interface for viewing upcoming episodes and premieres and updatting settings.
- **Dockerized**: Easy to deploy and manage as a Docker container.
- **Expandability**: Future features may include support for season packs, more selective retention rules, jellfin...

###Screen shots  

![html](https://github.com/Vansmak/OCDarr/assets/16037573/8fa0769c-6d6d-4104-90cd-2f15db437142)


## Installation

### Clone the Repository

Start by cloning the repository and navigating into the directory:

```
git clone https://github.com/Vansmak/OCDarr.git
cd OCDarr
```
Configuration
Environment Setup

Copy the provided .env.example to .env and update it with your Sonarr details:

```

cp .env.example .env
nano .env  # use your preferred text editor
```
Fill in the environment variables:
  
  SONARR_URL: URL to your Sonarr server.
  SONARR_API_KEY: Your Sonarr API key.
  
Docker Compose

Edit the docker-compose.yml file to suit your setup. Make sure the .env file is referenced correctly, and ports are mapped to your preference:
```
  version: '3.8'
  services:
    sonarr_script:
      build:
        context: .
        dockerfile: Dockerfile
      environment:
        
        SONARR_URL: ${SONARR_URL?Variable not set}
        SONARR_API_KEY: ${SONARR_API_KEY?Variable not set}
        CONFIG_PATH: /app/config/config.json
        
      env_file:
        - .env
  
      volumes:
        - .:/app
        - ./logs:/app/logs
        - ./config:/app/config
        - ./temp:/app/temp
      ports:
        - "5001:5001"
      restart: unless-stopped
```

Build and Run with Docker Compose

```

docker-compose up -d --build
```
This command builds the Docker image and runs it in detached mode.
Usage

Once your Docker container is running, it will listen for webhook calls from Tautulli when an episode is deemed as watched. Configure Tautulli to send webhooks to http://<docker-host-ip>:5001

![webhook](https://github.com/Vansmak/OCDarr/assets/16037573/cf0db503-d730-4a9c-b83e-2d21a3430ece)![webhook2](https://github.com/Vansmak/OCDarr/assets/16037573/45be66c2-1869-49c1-8074-9081ed7c913b)
![webhook3](https://github.com/Vansmak/OCDarr/assets/16037573/24f02a75-2100-4b2a-9137-ce1e68803d1f)![webhook4](https://github.com/Vansmak/OCDarr/assets/16037573/f82198fc-e4c4-40ec-a9c7-551b2d8cdccd)

json data exactly like:
```
{

"plex_title": "{show_name}",

"plex_season_num": "{season_num}",

"plex_ep_num": "{episode_num}"


}
```

Modify config.json to fine-tune behavior locally at /config/config.json or http://dockerurl:port  settings.

  get_option: '#' of episodes to get or 'season' for full seasons.
  action_option: 'search' to search episodes, 'monitor' to only monitor.
  already_watched: '#' of watched episodes to keep oe 'season'.
  always_keep: show names to keep even if delete is set, comma seperated

Additional Notes

  Set watched criteria in Tautulli general settings.
   
Troubleshooting

If you encounter issues, check the Docker container logs and logs/app.log and ensure all environment variables are correctly set.
