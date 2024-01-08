# 🎬 DiscordMovieBot - Ultimate content searching, suggestion, acquisition, and organization system 🌐

DiscordMovieBot is a simple Discord bot created to provide users with a robust set of tools for efficient torrent management and seamless online stream searching, all within the confines of a Discord server. The bot establishes a connection with a qbittorrent seedbox, providing your Discord users with an intuitive interface to effortlessly explore and obtain movies, TV shows, books, or add existing torrents via magnet links. DiscordMovieBot is simple in its design and does not use the Radarr/Jackett suite of software as a torrent collection management system. Instead, it utilizes custom api wrappers of popular trackers such as [1337x.to](https://1337x.to), [YIFY](https://yts.mx), [torrentdownload](https://torrentdownload.info), [Library Genesis](https://libgen.is/), and others, in conjunction with the qbittorrent Python API. This approach enables seamless, automated management of torrents directly to and from a qBittorrent instance.

## 📺 Demo

<div style="text-align: center;">
  <div style="display: inline-block; margin-right: 20px;">
    <p>Using /search to find movie/series torrents:</p>
      <img src="https://github.com/JakeTurner616/DiscordMovieBot/raw/807170d8301014c7da00fb4b59a10a9fd6aeacf2/docs/demo0.gif" alt="/search demo">
  </div>

  <div style="display: inline-block;">
    <p>Using /stream to find online movie/series streams:</p>
      <img src="https://github.com/JakeTurner616/DiscordMovieBot/blob/e9ee7c7a065fe25e0bff433976f7bd7346adc440/docs/demo2.gif" alt="/stream demo">    
  </div>
</div>

## 🔧 Pre-Install Setup

### qBittorrent setup:

1) Ensure that qBittorrent WebUI access with authentication is configured on the seedbox by enabling the webui feature and adding a user with a password.

3) Add qBittorrent categories for each media type that can be torrented via the leftmost ui panel: "movie", "tv", "fitgirl repack" each with a specified path to their desired download location.

### Discord bot setup:

1) Create a bot via the Discord developer portal making sure to enable message content intents.
   
3) Go to the OAuth URL generation page and give the bot the "bot" scope and all necessary permissions to send messages, reactions, embeds, read messages, embed links, add slash commands, and manage messages. Simply invite the bot to a server.

## 🛠️ DiscordMovieBot Installation

1) Clone and cd into the repo:
  `git clone https://github.com/JakeTurner616/DiscordMovieBot && cd DiscordMovieBot`

3) Setup a venv:
  `python -m venv discordmoviebot`

4) Activate the discordmoviebot venv:
   
    On Windows:
     `.\discordmoviebot\Scripts\activate`
      
    On macOS/Linux:
      `source discordmoviebot/bin/activate`

5) Install the requirements:
   `pip install -r requirements.txt`

6) Customize local configuration values within `config.ini`.

## 🚀 Deploying

  After configuring, DiscordMovieBot can be deployed by running bot.py within the venv. The backend Flask application is in non-production mode, and its port 5000 should not be forwarded unless a WSGI is used.

## 🕹️ Command Usage

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
