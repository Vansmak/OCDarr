#  <img src="https://github.com/Vansmak/OCDarr/assets/16037573/f802fece-e884-4282-8eb5-8c07aac1fd16" alt="logo" width="200"/>

Support This Project
If you find this project helpful, please consider supporting it. Your contributions help maintain and improve the project. Any support is greatly appreciated! ❤️ https://buymeacoffee.com/vansmak Thank you for your support!

OCDarr automates TV show maintenance in Sonarr based on Plex viewing activity via Tautulli. It ensures that the next episode is ready and cleans up watched episodes based on user-defined preferences. Ideal for keeping your media server tidy and your series up-to-date without manual intervention. Not useful for hoarders.  For example, sometimes I start an old show and never finish it, or takes awhile before I really get into it. So This way I dont have full seasons sitting there. I also do not have other users outside my household and am not a rewatcher of tv so I like to delete after a show is watched. This will always have the next episode ready to go and the last episode watched saved just in case.  If I need to protect a show because someone else is behind me then I can set certain shows to not delete.  If someone prefers getting full season instead of one episode you can do that. For example, if you have a new shows pilot episode only, once its watched the script can then monitor the rest of the season. Keep or delete previous episodes.  

## Features
- ** ADDED RULE_SETS, see below**
- **Dockerized**: Easy to deploy and manage as a Docker container.
    https://hub.docker.com/r/vansmak/ocdarr 
- **Automatic Episode Management**: Triggers searches for the next episode(s) or season in Sonarr based on viewing activity.
- **Space Management**: Optionally unmonitors and deletes watched episodes to save space.
- **Plex\Tautulli Integration**: Uses Tautulli webhook notifications to trigger actions automatically when episode is watched.
- **User Interface**: Simple HTML interface for viewing upcoming episodes and premieres and updatting settings.
- **Expandability**: Future features may include support for season packs, more selective retention rules, jellfin...

###Screen shots  

![ocdarr_dev](https://github.com/Vansmak/OCDarr/assets/16037573/5491d694-2e9a-46fb-a1f8-539dcaf661df)

the mobile branch uses a banner for artwork that I like better on mobile devuces. 

## Installation
Either:
### Clone the Repository

Start by cloning the repository and navigating into the directory:

```
git clone https://github.com/Vansmak/OCDarr.git
cd OCDarr
```
 After cloning the repository, switch to the main branch:
```
   cd OCDarr
   git checkout main
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


OR:

### Docker hub https://hub.docker.com/r/vansmak/ocdarr

Docker Instructions

   Pull the Docker Image
```
    docker pull vansmak/ocdarr:arch64 or amd64
```
  


   Set Environment Variables or

  Create an .env file with the required environment variables:
```
    SONARR_URL=http://sonarr.example.com
    SONARR_API_KEY=your_sonarr_api_key
```
  Run the Docker Container
```
    docker run -d \
      --env-file .env \
      --env CONFIG_PATH=/app/config/config.json \
      -p 5001:5001 \
      -v ${PWD}/logs:/app/logs \
      -v ${PWD}/config:/app/config \
      -v ${PWD}/temp:/app/temp \
      --restart unless-stopped \
      vansmak/ocdarr:amd64,arm64

```
###Usage
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

View html to see progress, fine-tune behavior and set rules locally at http://dockerurl:port.
Each rule has these four options

      get_option: '#' of episodes to get or 'season' for full seasons or 'all' for everything
  
      action_option: 'search' to search episodes, 'monitor' to only monitor.
  
      keep_watched: '#' of watched episodes to keep or 'season' to keep current seasons episodes only OR 'all' will keep everything (no deleting)
  
      monitor_watched: true or false, keep watched episodes monitored or not

** Making and assigning rules

      A show can only have one rule at a time.  I no rule is assigned then it will use the default rule.  Make sure you change the default rule to your preference.  If you select a new rule for a show it will reassign it. 
      Name them however it makes sense to you.
      !important: If you do not assign a show to a rule it will use the default rule.

Additional Notes

  Set watched criteria in Tautulli general settings. (consider % watched before webhook is sent)
   
Troubleshooting

If you encounter issues, check the Docker container logs and logs/app.log and ensure all environment variables are correctly set.
