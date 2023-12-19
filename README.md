# DiscordMoviebot - Ultimate content searching, suggestion, acquisition and organization system. 

## Overview

DiscordMoviebot is a Discord bot that aims to provide a complete set of tools for searching torrents, managing torrents, and streaming media to a discord server. The bot can connect to a qbittorrent seedbox and can utilize various torrent search engine APIs and offers features for finding and downloading both movies and TV shows in a convenient interface. Additionally, it includes functionality for downloading content from across the internet: YouTube, PBS, Libgen, and more.


<p align="center">
  <img src="https://github.com/JakeTurner616/DiscordMovieBot/raw/807170d8301014c7da00fb4b59a10a9fd6aeacf2/docs/demo0.gif" alt="/search demo">
</p>

## Pre-Install Setup
qBittorrent setup:

1) Ensure that qBittorrent WebUI access with authentication is configured on the seedbox, as sessions are managed automatically since [@8992c](https://github.com/JakeTurner616/DiscordMovieBot/commit/8992c8a2d2ff3434781b366aa3e9897d12699645).

3) Include qBittorrent categories for each media type that can be torrented: "movie", "tv", "fitgirl repack" each with a specified path to their desired download location. Take note of the movie and TV paths you choose here as they will be required when configuring the local `config.ini` variables.

Discord bot setup:

1) Create a bot via the Discord developer portal making sure to enable message content intents.
   
3) Go to the OAuth URL generation page and give the bot the "bot" scope and all necessary permissions to send messages, reactions, embeds, read messages, embed links, add slash commands, and manage messages. Simply invite the bot to a server.

## DiscordMovieBot Installation

1) Setup a venv:
  `python -m venv discordmoviebot`

2) Activate the discordmoviebot venv:
   
    On Windows:
     `.\discordmoviebot\Scripts\activate`
      
    On macOS/Linux:
      `source discordmoviebot/bin/activate`

3) Install the requirements:
   `pip install -r requirements.txt`

4) Customize local configuration values within `config.ini`.

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

- `/delete <optional_delete_index>`
  - Deletes either all active torrents or a select active torrent.

### TV Show Commands

- `/epsearch <TV Show Title>`
  - Searches for and displays an episode list for each season of a given TV show.

- `/tvsearch <TV Show Title SnnEnn>`
  - Searches a torrent search engine API and displays TV results as selectable embeds.

- `/advtvsearch <Movie Title>`
  - Searches torrent search engine on torrentdownload.info and displays TV results as selectable embeds.

- `/status <optional_delete_index>`
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

- `/diceroll <[optional int]d[int]>`
  - Rolls dice based on user input and displays result.
 
### Debug Commands

- `/debug`
  - Displays the debug menu.
