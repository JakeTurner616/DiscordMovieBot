# DiscordMoviebot - Ultimate content searching, suggestion, acquisition and organization system. 

## Overview

DiscordMoviebot is a Discord bot that aims to provide a complete set of tools for searching torrents, managing torrents, and streaming media to a discord server. The bot can connect to a qbittorrent seedbox and can utilize various torrent search engine APIs and offers features for finding and downloading both movies and TV shows in a convenient interface. Additionally, it includes functionality for downloading content from across the internet: YouTube, PBS, Libgen, and more.

## Pre-Install Setup
qBittorrent setup:

1) Make sure qBittorrent WebUI access with authentication is set up on the seedbox:

2) Setup an authentication bypass for the host running the bot by adding to the qbittorrent auth whitelist or checking the bypass auth on localhost box if the bot is running on the seedbox.

3) Add qBittorrent categories for each media type that can be torrented: "movie", "tv", "fitgirl repack" each with a path their desired download location. Note the movie and tv paths as they will be needed when setting configuration values later.

Discord setup:

1) Create a bot token on the discord dev portal, and enable message content intents.
   
3) Go to the OAuth URL generation page and give the bot the "bot" scope and all necessary permissions to send messages, reactions, embeds, read messages, embed links, add slash commands, and manage messages. Invite the bot to a server.

## Installation

1) Setup a venv:
  `python -m venv discordmoviebot`

2) Activate the discordmoviebot venv:
   
    On Windows:
     `.\discordmoviebot\Scripts\activate`
      
    On macOS/Linux:
      `source discordmoviebot/bin/activate`

3) Install the requirements:
   `pip install -r requirements.txt`

4) Customize configuration values within `config.ini`
     - Make sure the tv and movie save paths are the same as were set in the qBittorrent categories.

# Deploying

  After configuring, DiscordMovieBot can be deployed by running bot.py within the venv. The backend Flask application is in non-production mode, and its port 5000 should not be forwarded unless a WSGI is used.

## Command Usage

### Movie Commands

- `/search <Movie Title>`
  - Searches the 1337x torrent search engine API and displays movie results as selectable embeds.

- `/altsearch <Movie Title>`
  - Searches the yts torrent search engine API and displays movie results as selectable embeds.

- `/magnet <Magnet link> <category>`
  - Manually adds a magnet link to the torrent client. Must include a torrent category.

- `/delete`
  - Deletes all active torrents and all previous search result embeds.

### TV Show Commands

- `/epsearch <TV Show Title>`
  - Searches for and displays an episode list for each season of a given TV show.

- `/tvsearch <TV Show Title SnnEnn>`
  - Searches a torrent search engine API and displays TV results as selectable embeds.

- `/advtvsearch <Movie Title>`
  - Searches torrent search engine on torrentdownload.info and displays TV results as selectable embeds.

- `/status`
  - Shows all active torrents and allows for individual deletion of torrents.

### Streaming and Download Commands

- `/stream <query> <media_type> <optional download bool>`
  - Generates a link to stream any movie or show with an optional argument for basic downloading logic.

- `/youtube <YouTube title or link>`
  - Downloads a video from YouTube either from a link or through a search.

- `/pbsdownload <video_url>`
  - Downloads content from pbs.org or any PBS site.

- `/booksearch <title> <fiction/non-fiction>`
  - Searches and downloads books from libgen.

- `/simplebooksearch <title>`
  - Searches books from annas-archive without downloading them.

- `/pdfdownload <link> <filename>`
  - download books from a direct download link with a filename excluding the extension.

### Suggestion Commands

- `/suggest <Genre>`
  - Suggests a random movie based on genre by calling an API.

- `/aisuggest <Movie Title>`
  - Suggests a similar movie given a movie title by calling the g4f API.

- `/pick <Movie Title>`
  - Adds user picks to a queue.

- `/diceroll <[optional int]d[int]>`
  - Rolls dice based on user input and displays result.
 
### Debug Commands

- `/debug`
  - Displays the debug menu.
