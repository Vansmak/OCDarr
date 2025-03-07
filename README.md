Dev branch is developmental, consider it beta
#  <img src="https://github.com/Vansmak/OCDarr/assets/16037573/f802fece-e884-4282-8eb5-8c07aac1fd16" alt="logo" width="200"/>

[![Buy Me A Coffee](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/vansmak)

OCDarr automates TV show management in Sonarr based on your viewing activity. It ensures upcoming episodes are ready while cleaning up watched content according to your preferences. Perfect for viewers who:
- Want the next episode ready when they finish the current one
- Prefer to keep their media library tidy
- Don't need to keep entire seasons after watching
- Want different management rules for different shows
- Use with overseer or Jellyseer to manage at the episode level instead of full season

_Not designed for media hoarders or large household servers with multiple users at different points in series._
_Use is intended for owned media or paid supscription services._

## 🌟 Features

- **Smart Episode Management**: Automatically prepares upcoming episodes based on your watching patterns
- **Flexible Rules System**: Create and assign different management rules to shows
- **Media Server Integration**: 
  - Plex (via Tautulli)
  - Jellyfin (direct integration)
- **Automatic Tag Matching**: Shows requested through Overseerr/Jellyseerr/NZB360 can automatically use specific rules
- **Space Management**: Optional deletion of watched episodes based on your rules
- **User Interface**: Clean web interface for managing rules and viewing upcoming content
- **Containerized**: Easy deployment via Docker
- ***Request individual episodes
- ***Make custom requests
- ***Request from popular tmdb tests
- ***added Radarr w\o rule management
- ***Server page with links to your services

### Interface Preview
![OCDarr Interface](https://github.com/Vansmak/OCDarr/assets/16037573/5491d694-2e9a-46fb-a1f8-539dcaf661df)

_Optional banner view:_
![Banner View](https://github.com/user-attachments/assets/7db48f4e-7364-46c5-9c8b-449ddaed4de5)

## 📋 Requirements

- Sonarr v3
- Either:
  - Plex + Tautulli
  - OR Jellyfin
- Docker environment
- Overseerr/Jellyseerr (optional, for automatic rule assignment)

## 🚀 Installation

### Option 1: Docker Hub (Recommended)

```bash
# Pull the image
docker pull vansmak/ocdarr:amd64_dev

# Run the container
docker run -d \
  --name ocdarr \
  --env-file .env \
  --env CONFIG_PATH=/app/config/config.json \
  -p 5001:5001 \
  -v ${PWD}/logs:/app/logs \
  -v ${PWD}/config:/app/config \
  -v ${PWD}/temp:/app/temp \
  --restart unless-stopped \
  vansmak/ocdarr:latest
```
Option 2: Build from Source
```
git clone https://github.com/Vansmak/OCDarr.git
cd OCDarr
git checkout dev
docker-compose up -d --build
```
⚙️ Configuration
Environment Variables
Create a .env file:
```
SONARR_URL=http://sonarr.example.com
SONARR_API_KEY=your_sonarr_api_key
USE_POSTERS=true    # or false for banner view
CLIENT_ONLY=false   # true for viewing-only mode without management
```
Docker Compose
```
version: '3.8'
services:
  ocdarr:
    image: vansmak/ocdarr:amd64_dev
    environment:
      - SONARR_URL=${SONARR_URL}
      - SONARR_API_KEY=${SONARR_API_KEY}
      - CONFIG_PATH=/app/config/config.json
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
      - ./temp:/app/temp
    ports:
      - "5001:5001"
    restart: unless-stopped
```
📝 Rules System
Create rules using the OCDarr website (start with Default rule)
Rules define how OCDarr manages each show. Each rule has four components:

Get Option (get_option):  //breaking changes, labels are different than main branch, edit your config.json to match

    1 - Get only the next episode
    3 - Get next three episodes
    season - Get full seasons
    all - Get everything upcoming


Action Option (action_option):

    monitor - Only monitor episodes
    search - Monitor and actively search


Keep Watched (keep_watched):

    1 - Keep only last watched episode
    2 - Keep the last 2, etc
    season - Keep current season
    all - Keep everything


Monitor Watched (monitor_watched):

    true - Keep watched episodes monitored
    false - Unmonitor after watching



Rule Assignment
Shows can get rules in three ways:

Default Rule: Applied if no other rule matches
  This is the first rule you should edit to how you want most shows added as it will be applied if no other rule is 
  for example my Default rule is 
   ```
    "rules": {
        "Default": {
            "get_option": "1",
            "action_option": "search",
            "keep_watched": "1",
            "monitor_watched": true,
   ```
Manual Assignment: Through OCDarr's web interface
Automatic via Tags: When requesting shows through Overseerr/Jellyseerr if you dont add a tag then it will goto default.  
  If you use the "episodes" tag it will apply no rule and present you a form to select episodes you want, this is intended for one offs, not ongoing watch as you go
## 🔗 Media Server Integration

### Plex (via Tautulli) Setup

1. In Tautulli, go to Settings > Notification Agents
2. Click "Add a new notification agent" and select "Webhook"
3. Configure the webhook:
   - **Webhook URL**: `http://your-ocdarr-ip:5001/webhook`
   - **Trigger**: Episode Watched
   - **JSON Data**: Use exactly this template:

![webhook](https://github.com/Vansmak/OCDarr/assets/16037573/cf0db503-d730-4a9c-b83e-2d21a3430ece)![webhook2](https://github.com/Vansmak/OCDarr/assets/16037573/45be66c2-1869-49c1-8074-9081ed7c913b)
![webhook3](https://github.com/Vansmak/OCDarr/assets/16037573/24f02a75-2100-4b2a-9137-ce1e68803d1f)![webhook4](https://github.com/Vansmak/OCDarr/assets/16037573/f82198fc-e4c4-40ec-a9c7-551b2d8cdccd)

   ```json
   {
     "plex_title": "{show_name}",
     "plex_season_num": "{season_num}",
     "plex_ep_num": "{episode_num}"
   }
```
Important: Adjust your "Watched Percentage" in Tautulli's general settings to control when webhooks trigger.

Jellyfin Setup

In Jellyfin, go to Dashboard > Webhooks
Add a new webhook:

URL: http://your-ocdarr-ip:5001/jellyfin-webhook
Notification Type: Select "Playback Progress"



No template needed - Jellyfin sends structured data automatically. OCDarr processes events when playback reaches 45-55% of the episode.
Sonarr Webhook Setup
To enable automatic rule application when shows are added:

In Sonarr, go to Settings > Connect
Click the + button to add a new connection
Select "Webhook"
Configure:

URL: http://your-ocdarr-ip:5001/sonarr-webhook
Triggers: Enable "On Series Add"
Leave other settings at default



When a show is added to Sonarr:

If it has a tag matching a rule name -> that rule is applied
If no matching tag -> default rule is applied
The rule is applied to all monitored seasons

Example:

Create rule named "pilots" in OCDarr
Request show in Overseerr/Jellyseerr with "pilots" tag
When added to Sonarr, OCDarr will:

Detect the "pilots" tag
Apply the "pilots" rule configuration
Modify episode monitoring accordingly
Cancel any in-progress downloads that don't match the rule
