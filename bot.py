
import asyncio
import configparser
import platform
import random
import re
import subprocess
import time
import aiohttp
from bs4 import BeautifulSoup
import discord 
from discord import Option
from discord.ext import commands, menus
from discord import ui
import requests
import humanize
from qbittorrent import Client
from urllib.parse import quote
import nest_asyncio
from youtube_search import YoutubeSearch
import re
import aiohttp
import discord
from discord.ext import commands
import requests
import subprocess
import os
import shutil
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementNotInteractableException, ElementClickInterceptedException, UnexpectedAlertPresentException, WebDriverException, TimeoutException, StaleElementReferenceException, NoSuchElementException
import traceback  # Import the traceback module for better error logging
from urllib.parse import urlparse
intents = discord.Intents.default()
intents.message_content = True
nest_asyncio.apply()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 11.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
}
API_URL = 'http://127.0.0.1:5000'
def read_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config
config = read_config()
guilds = config.get('Bot', 'guild_ids')
guilds_list = [int(guild_id) for guild_id in guilds.split(',')]
# Function to check if the server is running
def is_server_running(url):
    try:
        response = requests.get(url)
        if response.status_code == 404:
            return True
        else:
            return False
    except requests.exceptions.ConnectionError:
        return False
subprocess_obj = None
# Check if the server is running
if not is_server_running(API_URL):
    print("Server is not running. Starting backend.py...")
    
    # Replace 'combined.py' with the actual filename if it's different
    python_script = "backend.py"
    # Launch the Python file using subprocess and capture the PID
    # Check the platform
    if platform.system() == "Windows":
        # For Windows
        subprocess_obj = subprocess.Popen([r".\discordmoviebot\Scripts\python.exe", python_script])
    else:
        # For other platforms (assuming 'python3' is the Python executable on non-Windows systems)
        subprocess_obj = subprocess.Popen(["python", python_script])
    # Wait for a few seconds to allow the server to start
    time.sleep(5)  # Adjust the sleep duration as needed
else:
    print("Server is already running.")
qb_host = config.get('qbit', 'host')
qb = Client(qb_host)
qb_user = config.get('qbit', 'user')
qb_pass = config.get('qbit', 'pass')
qb.login(qb_user, qb_pass) 
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')
# Create a dictionary to store search responses
search_responses = {}
# Create a dictionary to store progress messages for each torrent
torrent_progress_messages = {}
# Create a dictionary to store search responses
search_responses = {}

@bot.event
async def on_ready():
    
    server_url = config.get('qbit', 'host')
    try:
        response = requests.get(server_url)
        response.raise_for_status()  # Raise an exception for HTTP errors
    except requests.RequestException as req_ex:
        print(f"Connection to the server could not be established: {req_ex}")
        
        await bot.close()
        return
    print('Connected to the server. Starting bot...')
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
# Check the status from http://127.0.0.1:5000/infoglobal to see of a download is in progress upon bot start
    url = 'http://127.0.0.1:5000/infoglobal'
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if data:  # Check if the response is not empty
            torrent_name = data[0].get("name", "") # we should NEVER get an empty response here
            await bot.change_presence(activity=discord.Game(name=f'qBittorrent API - Downloading: {torrent_name}'), status=discord.Status.idle)
        else:
            await bot.change_presence(activity=None)
    else:
        print(f'Error fetching data from {url}') 
    print('------')
class EpisodeDropdown(discord.ui.Select):
    def __init__(self, options, placeholder, ctx, args):
        super().__init__(
            placeholder=placeholder,
            options=options
        )
        self.ctx = ctx  # Store the command context
        self.args = args  # Store the command arguments
    async def callback(self, interaction: discord.Interaction):
        selected_option = interaction.data['values'][0]
        character_to_trim_after = "∙"
        parts = selected_option.split(character_to_trim_after)
        parts[0].replace('.', '')
        # Retrieve the show title from the stored arguments
        (self.args)
messages = []
start_time = None  # Declare start_time outside of the download function

@bot.slash_command(
    name="youtube",
    guild_ids=guilds_list,
    description="Search YouTube or supply a YouTube video link for download",
)
async def youtube(ctx: discord.Interaction, yt_search: Option(str, description="Specify either a YouTube search or a video link", required=True)):
    global start_time  # Reference the global start_time variable
    start_time = time.time()  # Record the start time when the command is invoked
    initsearch_embed = discord.Embed(
                title=f"Searching Youtube for {yt_search}",
                color=discord.Color.blue()
            )
    await ctx.respond(embed=initsearch_embed)
    # Check if the query is a valid YouTube link
    if is_valid_youtube_link(yt_search):
        video_url = yt_search
        embed = discord.Embed(
            title="Download Started",
            description=f"Direct link provided. Downloading: {video_url}",
            color=discord.Color.green()
        )
        await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name=f'YT API - Downloading {video_url}'))
        # Send the embed message
        await ctx.send(embed=embed)
        # Call the function to start the download
        await start_yt_download(ctx, video_url)
    else:
        # Perform a search if the provided input is not a valid YouTube link
        results = YoutubeSearch(yt_search, max_results=5).to_dict()
        if not results:
            await ctx.send("No search results found.")
            return
        # Display search results as embeds with reactions
        for index, result in enumerate(results):
            title = result['title']
            thumbnail_url = result['thumbnails'][0]
            length = result['duration']
            channel = result['channel']
            embed = discord.Embed(title=title, description=f"Channel: {channel}\nLength: {length}", color=discord.Color.blue())
            embed.set_thumbnail(url=thumbnail_url)
            checkmark_emoji = '\u2705'  # Unicode checkmark emoji
            message = await ctx.send(embed=embed)
            await message.add_reaction(checkmark_emoji)
            messages.append(message)
        # Wait for user reaction
        def check(reaction, user):
            return user == ctx.author and reaction.emoji == '\u2705' and reaction.message.id in [msg.id for msg in messages]
        try:
            reaction, user = await bot.wait_for('reaction_add', check=check)
            # Debug prints
            print(f"Reaction emoji: {reaction.emoji}")
            print(f"Reaction message ID: {reaction.message.id}")
            # Find the selected index based on the position of the reaction in the list of reactions
            selected_index = messages.index(reaction.message)
            print(f"Selected index: {selected_index}")
            if 0 <= selected_index < len(results):
                selected_video = results[selected_index]
                video_url = f'https://youtube.com{selected_video["url_suffix"]}'
                embed = discord.Embed(
                    title="Download Started",
                    description=f"Downloading: {selected_video['title']}",
                    color=discord.Color.green()
                )
                await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name=f'YT API - Downloading {selected_video["url_suffix"]}'))
                # Send the embed message
                await ctx.send(embed=embed)
                # Call the function to start the download
                await start_yt_download(ctx, video_url)
            else:
                await print("Invalid selection index.")
        except TimeoutError:
            print("Timeout: You took too long to select a video.")
def is_valid_youtube_link(link):
    return "youtube.com" in link and "watch?v=" in link
async def start_yt_download(ctx, video_url):
    # Make the initial request to start the download
    async with aiohttp.ClientSession() as session:
        
        async with session.get(f'{API_URL}/download?url={video_url}') as response:
            data = await response.json()
    # Check if the download was successfully started
    if data.get('status') == 'success':
        end_time = time.time()
        # Calculate the elapsed time
        
        yt_complete_embed = discord.Embed(
            title="Download completed",
            description=f"Download completed for {video_url}.",
            color=discord.Color.green()
        )
         # Calculate the elapsed time
        elapsed_time_seconds = end_time - start_time
        # Format the elapsed time for display
        elapsed_time_str = format_elapsed_time(elapsed_time_seconds)
        yt_complete_embed.set_footer(text=f"Downloaded in: {elapsed_time_str}")
        # Respond to the interaction with the embed
        await bot.change_presence(activity=None)
        await ctx.respond(embed=yt_complete_embed)
def format_elapsed_time(seconds):
    # Calculate hours, minutes, and remaining seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    # Format the elapsed time based on the duration
    if hours >= 1:
        return f"{int(hours)} {'hour' if int(hours) == 1 else 'hours'}, {int(minutes)} {'minute' if int(minutes) == 1 else 'minutes'}"
    elif minutes >= 1:
        return f"{int(minutes)} {'minute' if int(minutes) == 1 else 'minutes'}, {int(seconds)} seconds"
    else:
        return f"{int(seconds)} seconds"
def convert_seconds_to_readable_time(seconds):
    # Convert seconds to a timedelta object
    duration = timedelta(seconds=seconds)
    # Extract days, hours, minutes, and seconds
    days = duration.days
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    # Format the time in a human-readable way
    if days > 0:
        return f"{days} day{'s' if days > 1 else ''}, {hours} hour{'s' if hours > 1 else ''}, {minutes} minute{'s' if minutes > 1 else ''}"
    elif hours > 0:
        return f"{hours} hour{'s' if hours > 1 else ''}, {minutes} minute{'s' if minutes > 1 else ''}"
    elif minutes > 0:
        return f"{minutes} minute{'s' if minutes > 1 else ''}"
    else:
        return f"{seconds} second{'s' if seconds > 1 else ''}"
def humanize_data(url):
    # Fetch data from the URL
    response = requests.get(url)
    data = response.json()
    # Humanize the information and store in a dictionary
    humanized_data = {}
    for index, download_info in enumerate(data):
        download_label = f"Download {index + 1}"
        humanized_data[download_label] = {
            "Title": download_info["name"],
            "Download Time": convert_seconds_to_readable_time(download_info["time_active"]),
            "Category": download_info["category"],
            "Progress Percentage": f"{download_info['progress'] * 100:.2f}%",
            "Hash": download_info["hash"]
        }
    return humanized_data
class TorrentButtons(discord.ui.View):
    def __init__(self, downloads):
        super().__init__()
        self.downloads = downloads
    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        # Parse the custom_id to get the download index
        download_index = int(button.custom_id.split('_')[1])
        # Fetch the corresponding hash based on the index
        hash_to_delete = self.downloads[download_index - 1]["Hash"]
        # Delete the torrent using Flask route
        delete_url = f'http://127.0.0.1:5000/delete/{hash_to_delete}'
        requests.delete(delete_url)
        # Respond to the button click
        await interaction.response.edit_message(content=f"Download {download_index} deleted successfully.", view=self)

@bot.slash_command(name="status", description="Get download information", guild_ids=guilds_list)
async def status(ctx: discord.Interaction):
    try:
    # Check the status from http://127.0.0.1:5000/infoglobal to see of a download is in progress upon bot start
        url = 'http://127.0.0.1:5000/infoglobal'
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if data:  # Check if the response is not empty
                torrent_name = data[0].get("name", "") # we should NEVER get an empty response here
                await bot.change_presence(activity=discord.Game(name=f'qBittorrent API - Downloading: {torrent_name}'), status=discord.Status.idle)
            else:
                await bot.change_presence(activity=None)
        else:
            print(f'Error fetching data from {url}') 
        data = requests.get(url).json()
        # Check the number of active downloads
        num_downloads = len(data)
        # Create an embed
        embed = discord.Embed(
            color=discord.Color.green()
        )
        # Set the title and description
        title = f"{num_downloads} download{'s' if num_downloads != 1 else ''} currently active"
        embed.title = title
        # Add the humanized data to the embed
        for index, download_info in enumerate(data):
            # Humanize Download Time
            download_time_seconds = int(download_info['time_active'])
            download_time_readable = str(datetime.timedelta(seconds=download_time_seconds))
            # Humanize Progress Percentage
            progress_percentage = float(download_info['progress']) * 100
            progress_percentage_readable = f"{progress_percentage:.2f}%"
            embed.add_field(
                name=f"Download {index + 1}: {download_info['name']}",
                value=f"Category: {download_info['category']}\n"
                      f"Download Time: {download_time_readable}\n"
                      f"Progress Percentage: {progress_percentage_readable}\n"
                      f"Hash: {download_info['hash']}",
                inline=False
            )
        # Create a view with buttons for each download
        view = TorrentButtons(downloads=data)
        # Add buttons for each download
        for i, download_info in enumerate(data):
            button_label = f"Delete {i + 1}"
            button = discord.ui.Button(style=discord.ButtonStyle.red, label=button_label, custom_id=f"delete_{i + 1}")
            view.add_item(button)
        # Send the message with the embed and buttons
        await ctx.respond(embed=embed, view=view, ephemeral=True)
    except Exception as e:
        # If an exception occurs, send an ephemeral error embed
        error_embed = discord.Embed(
            title="Error",
            description=f"An error occurred: {e}",
            color=discord.Color.red()
        )
        await ctx.respond(embed=error_embed, ephemeral=True)
# Define the URL of the Flask API
API_EP_URL = "http://127.0.0.1:5000/episodes"
# Dictionary to store searched titles for each user
searched_titles = {}

@bot.slash_command(name="epsearch", description="Search for TV show episodes", guild_ids=guilds_list)
async def epsearch(ctx, 
                  title: Option(str, description="Specify the title of the TV show you want to search for.", required=True)):
    # Create an initial loading embed
    loading_embed = discord.Embed(title="Loading...", color=0x4287f5)
    loading_message = await ctx.respond(embed=loading_embed, ephemeral=False)
    # Format the title for URL encoding
    formatted_title = quote(title)
    # Store the searched title in the dictionary, using the user's Discord ID as the key
    searched_titles[ctx.author.id] = title
    # Make a request to the Flask API with the formatted title
    response = requests.get(f"{API_EP_URL}?title={formatted_title}")
    if response.status_code == 200:
        data = response.json()
        if "show_info" in data:
            show_info = data["show_info"]
            if not show_info:
                await loading_message.delete()  # Remove the loading embed
                await ctx.send("No TV show results found.")
                return
            # Automatically select the first result (index 0)
            selection = 0
            title = searched_titles.get(ctx.author.id, "")
            url = show_info[selection]["url"]
            # Make a request to the Flask API with the title and selection
            response = requests.get(f"{API_EP_URL}?title={title}&selection={selection}", timeout=100)
            if response.status_code == 200:
                data = response.json()
                if "episode_names" in data:
                    episode_names = data["episode_names"]
                    # Split episodes into chunks of 25
                    chunk_size = 25
                    chunked_episodes = [episode_names[i:i + chunk_size] for i in range(0, len(episode_names), chunk_size)]
                    dropdown_views = []
                    for chunk in chunked_episodes:
                        options = [
                            discord.SelectOption(label=episode, value=episode)
                            for episode in chunk
                        ]
                        placeholder = f''
                        dropdown = EpisodeDropdown(options, placeholder, ctx, title)
                        view = discord.ui.View()
                        view.add_item(dropdown)
                        dropdown_views.append(view)
                    for view in dropdown_views:
                        await ctx.send("", view=view)
                else:
                    await loading_message.delete()  # Remove the loading embed
                    await ctx.send("No episode names found for the selected TV show.")
            else:
                await loading_message.delete()  # Remove the loading embed
                await ctx.send(f"Failed to retrieve episode names. Status code: {response.status_code}")
        else:
            await loading_message.delete()  # Remove the loading embed
            await ctx.send("No TV show results found.")
    else:
        await loading_message.delete()  # Remove the loading embed
        await ctx.send(f"Failed to retrieve TV show data. Status code: {response.status_code}")
# Define the IMDb API route
imdb_api_url = f'{API_URL}/spellcheck'
def get_first_movie_title(search_query):
    # Send a GET request to the IMDb API route
    response = requests.get(imdb_api_url, params={'search': search_query})
    if response.status_code == 200:
        movie_info = response.json()
        if movie_info:
            # Get the first movie title
            return movie_info[0]['title']
        else:
            return None  # Return None if no movie titles are found
    else:
        return None  # Return None if API request fails
    
def get_first_movie_year(search_query):
    # Send a GET request to the IMDb API route
    response = requests.get(imdb_api_url, params={'search': search_query})
    if response.status_code == 200:
        movie_info = response.json()
        if movie_info:
            # Get the first movie title
            return movie_info[0]['year']
        else:
            return None  # Return None if no movie titles are found
    else:
        return None  # Return None if API request fails

@bot.slash_command(
    name="altsearch",
    description="Search for movies on YTS.mx",
    guild_ids=guilds_list
)
async def altsearch(ctx, 
                   search_query: Option(str, description="Specify the title of the movie you want to search for.", required=True)):
    """Sends a request and returns JSON response as selectable embedded messages."""
    # Send an initial "Searching for {Movie Title}" embed
    initial_embed = discord.Embed(
        title=f"Searching for {search_query}",
        color=discord.Color.blue()
    )
    initial_message = await ctx.respond(embed=initial_embed, ephemeral=False)
    url = f'http://127.0.0.1:5000/torrents-yts?search={search_query}'
    global download_in_progress  # Declare the global variable
    async with ctx.typing():
        try:
            response = requests.get(url)
            data = response.json()
            if "error" in data[0] and data[0]["error"] == "Movie not found on YTS":
                error_embed = discord.Embed(
                    title='No Results Found',
                    description='No torrents match your search query on YTS.mx.',
                    color=discord.Color.red()
                )
                await initial_message.edit(embed=error_embed)
                # Check if there's a valid response from IMDb API
                first_movie_title = get_first_movie_title(search_query)
                first_movie_year = get_first_movie_year(search_query)
                if first_movie_title and first_movie_year:
                    first_movie_title_cleaned = first_movie_title.replace(' ','%20')
                    spellcheck_embed = discord.Embed(
                        title=f'Did you mean: {first_movie_title} ({first_movie_year})',
                        description=f'[IMDb search results](https://www.imdb.com/find/?q={first_movie_title_cleaned}&ref_=nv_sr_sm)',
                        color=discord.Color.blue()
                    )
                    spellcheck_embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/IMDB_Logo_2016.svg/2560px-IMDB_Logo_2016.svg.png")
                    await ctx.send(embed=spellcheck_embed)  # Send the spellcheck as a reply
                return
            search_responses[ctx.author.id] = data  # Store the search responses for the user
            for item in data:
                title = item['title']
                full_link = item['link']
                seeds = item['seeds']
                leeches = item['leeches']
                size = item['size']
                image_url = item.get('cover_image_url', 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT1mcHVzLjjPjJNNYOT8v2f0rYU2C5wzvf_BnvhayR8N6ENCTXSP9quG0ejpmJ2w6EBWYw&usqp=CAU')  # Get the image URL if available
                description = f"Link: {full_link}\nSeeds: {seeds}\nLeeches: {leeches}\nSize: {size}"
                if not image_url:
                    image_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT1mcHVzLjjPjJNNYOT8v2f0rYU2C5wzvf_BnvhayR8N6ENCTXSP9quG0ejpmJ2w6EBWYw&usqp=CAU"
                embed = discord.Embed(
                    title=title,
                    description=description,
                    color=discord.Color.blue()
                )
                if image_url:
                    embed.set_image(url=image_url)  # Set the image URL as the embed image
                message = await ctx.send(embed=embed)
                await message.add_reaction('\u2705')  # Add a checkmark emoji as a reaction
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="search", description="Search for movies by title", guild_ids=guilds_list
)
async def search(ctx, 
                title: Option(str, description="Specify the title of the movie you want to search for.", required=True)):
    # Define the initial embed for the "Searching for..." message
    initial_embed = discord.Embed(
        title=f"Searching for {title}...",
        description="Please wait while we fetch the results.",
        color=discord.Color.blurple()
    )
    # Send the initial embed as a response to the slash command
    await ctx.respond(embed=initial_embed, ephemeral=False)
    url = f'http://127.0.0.1:5000/torrents?search={title}'
    global download_in_progress  # Declare the global variable
    try:
        async with ctx.typing():  # Simulate typing while processing
            response = requests.get(url)
            data = response.json()
        # Stop typing and start sending messages
        await ctx.trigger_typing()  # Show the typing indicator for a brief moment
        if not data:  # If the response is empty
            error_embed = discord.Embed(
                title='No Results Found',
                description='No torrents match your search query on 1337x.to.',
                color=discord.Color.red()
            )
            # Send the error embed
            await ctx.respond(embed=error_embed, ephemeral=False)
            # Call altsearch with the same search query
            await ctx.invoke(altsearch, search_query=title)
            return
        search_responses[ctx.author.id] = data  # Store the search responses for the user
        for item in data:
            title = item['title']
            full_link = item['link']
            seeds = item['seeds']
            leeches = item['leeches']
            size = item['size']
            image_url = item.get('cover_image_url', 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT1mcHVzLjjPjJNNYOT8v2f0rYU2C5wzvf_BnvhayR8N6ENCTXSP9quG0ejpmJ2w6EBWYw&usqp=CAU')  # Get the image URL if available
            description = f"Link: {full_link}\nSeeds: {seeds}\nLeeches: {leeches}\nSize: {size}"
            embed = discord.Embed(
                title=title,
                description=description,
                color=discord.Color.blue()
            )
            if image_url:
                embed.set_image(url=image_url)  # Set the image URL as the embed image
            # Send the results as separate messages
            message = await ctx.send(embed=embed)
            # Add a green checkmark emoji reaction to each result
            await message.add_reaction('\u2705')
    except Exception as e:
        await ctx.respond(f"An error occurred: {e}", ephemeral=True)
mirror_list = [
    # https//movie-web.app (Average = 13.25 ms)
    'https://movie-web.app',
    # Mirrors ordered by latency to Denver:
    # https://movie-web-lac.vercel.app/# (Average = 10.5 ms)
    'https://movie-web-lac.vercel.app/#',
    # https://h-matheo-github-io.vercel.app/# (Average = 10.25 ms)
    'https://h-matheo-github-io.vercel.app/#',
    # https://watch.testersquad.tk/# (Average = 11.0 ms)
    'https://watch.testersquad.tk/#',
    # https://retrofiber.github.io/RetroTV/# (Average = 11.25 ms)
    'https://retrofiber.github.io/RetroTV/#',
    # https://filmzly.com/# (Average = 11.75 ms)
    'https://filmzly.com/#',
    # https://oldmov.vercel.app/# (Average = 11.75 ms)
    'https://oldmov.vercel.app/#',
    # https://themysteriouscookie.vercel.app/# (Average = 11.25 ms)
    'https://themysteriouscookie.vercel.app/#',
    # https://cjidnqpi.github.io/# (Average = 12.0 ms)
    'https://cjidnqpi.github.io/#',
    # https://movies.rubby.app/# (Average = 15.0 ms)
    'https://movies.rubby.app/#',
    # https://magikmovies.xenia.lol/#: (Average = 149.25 ms)
    'https://magikmovies.xenia.lol/#',
    # https://betasse-movie.fun/#: (Average = 139.0 ms)
    'https://betasse-movie.fun/#'
]

@bot.slash_command(
    name="stream",
    description="Search for a series or movie on movie-web.app",
    guild_ids=guilds_list
)
async def stream(
    ctx,
    title: Option(
        str,
        description="Specify the title",
        required=True,
    ),
    
    # Description: "Title of the series or movie to search for."
    media_type: Option(
        str,
        description="Specify the media type",
        required=True,
        choices=["series", "movie"]
    ),
    download: Option(
        bool,
        description="Specify whether to initiate a download",
        required=False,
        default=False
    )
):
    final_link = None  # Initialize to None
    # Check if the query is a valid URL using regex
    if re.match(r'^https?://', title):
        final_link = title
        
        await ctx.respond(embed=discord.Embed(title="Stream", description=f"\nClick [here]({final_link}) to view the content.", color=discord.Color.blue()))
        embed.set_thumbnail(url="https://raw.githubusercontent.com/JakeTurner616/stream-app/main/android-chrome-512x512.png")
    else:
        for mirror in mirror_list:
            try:
                response = requests.head(mirror, headers=headers)
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
            except requests.exceptions.RequestException as e:
                # Handle any exception (e.g., ConnectionError) and proceed to the next mirror
                print(f"Mirror {mirror} is not reachable. Trying the next one.")
                continue
            
            search_link = f"{mirror}/search/{media_type}/{title.replace(' ', '%20')}"
            break
        else:
            # If none of the mirrors are available, handle the error
            error_embed = discord.Embed(title="Error", description="All mirrors are unreachable.", color=discord.Color.red())
            await ctx.respond(embed=error_embed)
            return
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        driver = webdriver.Chrome(options=chrome_options)
        embed = discord.Embed(title=f"Searching for the {media_type} \"{title}\"...", color=discord.Color.blue())
        response_msg = await ctx.respond(embed=embed)
        try:
            # Open the search link in the browser
            driver.get(search_link)
            print(f"search link: {search_link}")
            # Wait for the element with the specific CSS selector to be present on the page
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.grid > a'))
            )
            # Find the element with the specific CSS selector
            specific_element = driver.find_element(By.CSS_SELECTOR, '.grid > a')
            # Get the href attribute of the element
            result_link = specific_element.get_attribute('href')
            # Combine the result link with the base URL
            final_link = r"https://" + result_link.replace(mirror_list[0], 'movie.serverboi.org/#')
            print(f"final link: {final_link}")
            # Create an embed with the final link
            embed = discord.Embed(title=f"Search result for the {media_type}: \"{title}\"", description=f"\nClick [here]({final_link.replace('movie.serverboi.org/#', 'movie-web.app')}) to view the online stream.", color=discord.Color.blue())
            embed.set_thumbnail(url="https://raw.githubusercontent.com/JakeTurner616/stream-app/main/android-chrome-512x512.png")
            # Send a follow-up message with the final link and image
            await ctx.followup.send(embed=embed)
        except NoSuchElementException:
            # Handle the case when the page elements cannot be found
            error_embed = discord.Embed(title="Error", description="Page elements not found.", color=discord.Color.red())
            await ctx.followup.send(embed=error_embed)
        except TimeoutException:
            # Handle the case when the page cannot be reached within the timeout
            error_embed = discord.Embed(title="Error", description="No results found.", color=discord.Color.red())
            await ctx.followup.send(embed=error_embed)
        except StaleElementReferenceException:
            # Handle the case when the page cannot be reached within the timeout
            error_embed = discord.Embed(title="Error", description="Element is no longer valid, a StaleElementReferenceException has been raised indicating that the reference to the element is now stale or outdated.", color=discord.Color.red())
            await ctx.followup.send(embed=error_embed)
        except ElementNotInteractableException:
            error_embed = discord.Embed(title="Error", description="Element is not in an interactable state.", color=discord.Color.red())
            await ctx.followup.send(embed=error_embed)
        except ElementClickInterceptedException:
            error_embed = discord.Embed(title="Error", description="Click intercepted by another element.", color=discord.Color.red())
            await ctx.followup.send(embed=error_embed)
        except UnexpectedAlertPresentException:
            error_embed = discord.Embed(title="Error", description="Unexpected alert present on the page.", color=discord.Color.red())
            await ctx.followup.send(embed=error_embed)
        except WebDriverException as e:
            error_embed = discord.Embed(title="Error", description=f"WebDriverException: {str(e)}", color=discord.Color.red())
            await ctx.followup.send(embed=error_embed)
        finally:
            # Ensure the WebDriver is closed after usage
            driver.quit()
    # Check if download is requested and final_link is not None
    if download and final_link is not None:
        # Use the Discord bot function to initiate the file download
        download_file_discord(final_link)
# Existing function to initiate download via Flask route
def download_file_discord(final_link):
    flask_route_url = 'http://127.0.0.1:5000/download_stream?url=' + final_link
    response = requests.get(flask_route_url)
    if response.status_code == 200:
        print(f"File download initiated.")
    else:
        print(f"Error initiating file download.")
        print(response.json())
# Now you can use the shared function in both commands
def format_season_episode(query):
    # Define a regular expression pattern to match "sXeY" or "sXYeYZ" where X and Y are numbers
    pattern = r's(\d{1,2})e(\d{1,2})'
    match = re.search(pattern, query)
    
    if match:
        season = match.group(1).zfill(2)  # Format as "s01"
        episode = match.group(2).zfill(2)  # Format as "e01"
        formatted_query = re.sub(pattern, f's{season}e{episode}', query)
    else:
        formatted_query = query
        season = "00"  # Default season value
        episode = "00"  # Default episode value
    
    return formatted_query, season, episode

@bot.slash_command(
    name="tvsearch",
    description="Search for TV show torrents on 1337x.to",
    guild_ids=guilds_list
)
async def tvsearch(ctx, 
                  search_query: Option(str, description="Specify the title of the TV show you want to search for.", required=True)):
    # Extract and format season and episode numbers from the user input (if found)
    formatted_query, search_season, search_episode = format_season_episode(search_query)
    # Define the initial embed for the "Searching for..." message
    initial_embed = discord.Embed(
        title=f"Searching for {search_query}...",
        description="Please wait while we fetch the results.",
        color=discord.Color.blurple()
    )
    # Send the initial embed as a response
    initial_message = await ctx.respond(embed=initial_embed, ephemeral=False)
    url = f'http://127.0.0.1:5000/tv?search={formatted_query}'
    global download_in_progress  # Declare the global variable
    try:
        async with ctx.typing():  # Simulate typing while processing
            response = requests.get(url)
            data = response.json()
        # Stop typing and start sending messages
        await ctx.trigger_typing()  # Show the typing indicator for a brief moment
        if not data:  # If the response is empty
            error_embed = discord.Embed(
                title='No Results Found',
                description='No TV torrents match your search query on 1337x.to.',
                color=discord.Color.red()
            )
            # Send the error embed
            await ctx.send(embed=error_embed)
            # Call advtvsearch with the same search query
            await ctx.invoke(advtvsearch, search_query=search_query)
            return
        search_responses[ctx.author.id] = data  # Store the search responses for the user
        for item in data:
            title = item['title']
            full_link = item['link']
            seeds = item['seeds']
            leeches = item['leeches']
            size = item['size']
            image_url = item.get('cover_image_url', 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT1mcHVzLjjPjJNNYOT8v2f0rYU2C5wzvf_BnvhayR8N6ENCTXSP9quG0ejpmJ2w6EBWYw&usqp=CAU')  # Get the image URL if available
            description = f"Link: {full_link}\nSeeds: {seeds}\nLeeches: {leeches}\nSize: {size}"
            embed = discord.Embed(
                title=title,
                description=description,
                color=discord.Color.blue()
            )
            if image_url:
                embed.set_image(url=image_url)  # Set the image URL as the embed image
            # Send the results as separate messages
            message = await ctx.send(embed=embed)
            # Add a green checkmark emoji reaction to each result
            await message.add_reaction('\u2705')
    except Exception as e:
        error_embed = discord.Embed(
            title='An Error Occurred',
            description=f"An error occurred while fetching the results: {e}",
            color=discord.Color.red()
        )
        # Send the error embed
        await initial_message.edit(embed=error_embed)

@bot.slash_command(
    name="advtvsearch",
    description="Search for TV show torrents on torrentdownload.info",
    guild_ids=guilds_list
)
async def advtvsearch(ctx, search_query: Option(str, description="Specify the title of the TV show you want to search for.")):
    # Extract and format season and episode numbers from the user input (if found)
    formatted_query, search_season, search_episode = format_season_episode(search_query)
    # Define the initial embed for the "Searching for..." message
    initial_embed = discord.Embed(
        title=f"Searching for {search_query}...",
        description="Please wait while we fetch the results.",
        color=discord.Color.blurple()
    )
    # Send the initial embed as a response
    initial_message = await ctx.respond(embed=initial_embed, ephemeral=False)
    url = f'http://127.0.0.1:5000/advtv?search={formatted_query}&selection=1'  # Added "&" to separate query parameters
    global download_in_progress  # Declare the global variable
    try:
        async with ctx.typing():  # Simulate typing while processing
            response = requests.get(url)
            data = response.json()
        # Stop typing and start sending messages
        await ctx.trigger_typing()  # Show the typing indicator for a brief moment
        if not data:  # If the response is empty
            error_embed = discord.Embed(
                title='No Results Found',
                description=f'No TV torrents match your search query on torrentdownload.info',
                color=discord.Color.red()
            )
            # Send the error embed
            await ctx.send(embed=error_embed)
            return
        # Ensure that the data is a list
        if isinstance(data, list):
            search_responses[ctx.author.id] = data  # Store the search responses for the user
            for item in data:
                title = item.get('title', 'Title not found')  # Get the title if available
                full_link = item.get('link', 'Link not found')  # Get the link if available
                seeds = item.get('seeds', 0)  # Get the seeds if available, default to 0 if not found
                leeches = item.get('leeches', 0)  # Get the leeches if available, default to 0 if not found
                size = item.get('size', 'Size not found')  # Get the size if available
                image_url = item.get('cover_image_url', 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT1mcHVzLjjPjJNNYOT8v2f0rYU2C5wzvf_BnvhayR8N6ENCTXSP9quG0ejpmJ2w6EBWYw&usqp=CAU')  # Get the image URL if available
                description = f"Link: {full_link}\nSeeds: {seeds}\nLeeches: {leeches}\nSize: {size}"
                embed = discord.Embed(
                    title=title,
                    description=description,
                    color=discord.Color.blue()
                )
                if image_url:
                    embed.set_image(url=image_url)  # Set the image URL as the embed image
                # Send the results as separate messages
                message = await ctx.send(embed=embed)
                # Add a green checkmark emoji reaction to each result
                await message.add_reaction('\u2705')
    except Exception as e:
        error_embed = discord.Embed(
            title='An Error Occurred',
            description=f"An error occurred while fetching the results: {e}",
            color=discord.Color.red()
        )
        # Send the error embed
        await initial_message.edit(embed=error_embed)

@bot.slash_command(name="debug", description="Get debug information", guild_ids=guilds_list
)
async def slash_command(interaction: discord.Interaction):
    downloading = download_in_progress
    # Check if a URL returns a 404 status
    url_to_check = "http://127.0.0.1:5000/"  # Replace with the URL you want to check
    start_time = time.time()  # Move the start time after defining the URL
    response = requests.get(url_to_check)
    if response.status_code == 404:
        is_backend_valid = True
    else:
        is_backend_valid = False
    # Create an embed
    embed = discord.Embed(
        title="Debug Information",
        color=discord.Color.red()  # You can customize the color
    )
    # Add the variables to the embed
    embed.add_field(name="download_in_progress:", value=downloading)
    embed.add_field(name="is_backend_valid:", value=is_backend_valid)
    image_url = "https://status.serverboi.org/api/badge/7/avg-response"
    
    # Add the image to the embed
    embed.set_image(url=image_url)
    # Calculate the command timing in milliseconds
    end_time = time.time()
    elapsed_time = (end_time - start_time) * 1000  # Convert to milliseconds
    # Format the command timing
    elapsed_time_formatted = "{:.2f} ms".format(elapsed_time)
    # Calculate and format the URL response time in milliseconds
    response_time = response.elapsed.total_seconds() * 1000  # Convert to milliseconds
    response_time_formatted = "{:.2f} ms".format(response_time)
    # Add the command timing and response time as the footer
    embed.set_footer(text=f"Backend response time: {response_time_formatted} | !debug response time: {elapsed_time_formatted}")
    # Send the embed as a message in response to the interaction
    await interaction.response.send_message(embed=embed) 

@bot.slash_command(name="delete", description="Delete all active torrents search result emebds", guild_ids=guilds_list
)
async def delete(ctx):
    print("DELETE LOGIC HAS BEEN FIRED")
    await bot.change_presence(status=discord.Status.online, activity=None)
    
    global download_in_progress  # Declare the global variable and make it accessible
    # Check if a download is in progress, and if so, set it to False
    if download_in_progress:
        download_in_progress = False
    # Delete all previous messages in the channel
    async for message in ctx.channel.history(limit=200):
        if message.embeds:
            embed = message.embeds[0]
            if (
                embed.title and (
                    embed.title.startswith("Download completed") or
                    embed.title.startswith("Movie suggestion") or
                    embed.title.startswith("Error:") or
                    embed.title.startswith("Episode Names") or
                    embed.title.startswith("Searching for") or
                    embed.title.startswith("Search result for the") or
                    embed.title.startswith("Searching for the") or
                    embed.title.endswith(")")
                )
            ):
                # Message meets one of the specified conditions, so we ignore it
                continue
            else:
                await message.delete()
    # Make the HTTP request to delete torrents
    delete_url = 'http://127.0.0.1:5000/delete'
    delete_response = requests.get(delete_url)
    try:
        delete_content = delete_response.json().get('message', 'No message found in response.')
    except ValueError:
        delete_content = 'Invalid JSON response.'
    # Create an embed with the delete response content
    embed = discord.Embed(
        title=delete_content,
        color=discord.Color.green()
    )
    # Respond with the embed as a direct response to the slash command
    await ctx.respond(embed=embed, ephemeral=False)
# Define a global variable to track whether a download is in progress
download_in_progress = False

@bot.slash_command(name="magnet", description="Download a torrent from a magnet link.", guild_ids=guilds_list)
async def magnet(ctx, 
                magnet_link: Option(str, description="Specify the magnet link.", required=True),
                category: Option(str, description="Specify the download category.", required=True, choices=["TV", "Movie", "FitGirl Repack"])):
    
    category = category.lower()
    global download_in_progress
    empty_response_counter = 0
    movie_title = None
    # Initialize a counter for metadata download failures
    metadata_failure_count = 0
    max_metadata_failure_count = 100  # The maximum number of allowed failures
    try:
        if category == "movie":
            category = "Movie"
        if category == "tv":
            category = "TV"
        if category == "FitGirl Repack":
            category = "fitgirl repack"
        if not category:
            await ctx.send("Must supply a category of either TV, Movie or Repack using `/magnet <MagnetLink> <Category>`")
            return
        # Set the flag to indicate that a download is in progress
        download_in_progress = True
        qb.download_from_link(magnet_link, category=category)
        if category == "movie":
            category = "Movie"
        # Create a slash command response progress embed
        init_embed = discord.Embed(
            title="The torrent file is being sent to qittorrent.",
            color=discord.Color.green()
        )
        progress_message = await ctx.respond(embed=init_embed, ephemeral=False)
        # Create a updatable progress embed
        progress_embed = discord.Embed(
            title="Torrent download initiated",
            color=discord.Color.green()
        )
        progress_message = await ctx.send(embed=progress_embed)
        while True:
            info_global_url = 'http://127.0.0.1:5000/infoglobal'
            info_response = requests.get(info_global_url).json()
            if info_response:
                print("info_response:", info_response)  # Debug statement
                if not download_in_progress:
                    
                    download_in_progress = True
                    empty_response_counter = 0  # Reset the counter
                    movie_title = info_response[0].get('name', 'Unknown Name')
                    break
                else: 
                    movie_title = 'unknown torrent title'
                    
            elif download_in_progress:
                # Increment the empty response counter
                empty_response_counter += 1
                print(f"empty response: {empty_response_counter}")
            
            if empty_response_counter >= 10:
                
                if category == "Movie":
                    download_complete_embed = discord.Embed(
                        title=f'Download completed for {movie_title} (Movie)!',
                        color=discord.Color.green()
                    )
                elif category == "TV":
                    download_complete_embed = discord.Embed(
                        title=f'Download completed for {movie_title} (TV)!',
                        color=discord.Color.green()
                    )
                elif category == "fitgirl repack":
                    download_complete_embed = discord.Embed(
                        title=f'Download completed for {movie_title} (FitGirl Repack)!',
                        color=discord.Color.green()
                    )
                
                # Delete the initial response
                await progress_message.delete()
                # Send the new embed as a response
                await ctx.send(embed=download_complete_embed)
                
                await bot.change_presence(status=discord.Status.online, activity=None)
                download_in_progress = False
                break
            if info_response:  # Check info_response again to avoid potential error
                category = info_response[0].get('category', '')
                name = info_response[0].get('name', 'Unknown Name')
                state = info_response[0].get('state', 'Unknown State')
                # Check if "metaDL" is in the state field
                if "metaDL" in state:
                    metadata_failure_count += 1
                    print(metadata_failure_count, info_response)  # Debug statement
                    if metadata_failure_count >= max_metadata_failure_count:
                        error_embed = discord.Embed(
                            title=f'Error: Failed to download metadata for {name}!',
                            description=f"The download has encountered repeated metadata download failures. Either the VPN is fucked or the torrent had no peers.",
                            color=discord.Color.red()
                        )
                        download_in_progress = False
                        await ctx.send(embed=error_embed)
                        metadata_failure_count = 0
                        # Check the status from http://127.0.0.1:5000/infoglobal to see of another download is in progress
                        url = 'http://127.0.0.1:5000/infoglobal'
                        response = requests.get(url)
                        
                        if response.status_code == 200:
                            data = response.json()
                            if data:  # Check if the response is not empty
                                torrent_name = data[0].get("name", "") # we should NEVER get an empty response here
                                await bot.change_presence(activity=discord.Game(name=f'qBittorrent API - Downloading: {torrent_name}'), status=discord.Status.idle)
                            else:
                                await bot.change_presence(activity=None)
                        else:
                            print(f'Error fetching data from {url}') 
                        break  # Break out of the loop
                size = info_response[0].get('size', 0)
                downloaded = info_response[0].get('downloaded', 0)
                eta_seconds = info_response[0].get('eta', 0)
                eta_humanized = humanize.naturaldelta(eta_seconds)
                num_seeds = info_response[0].get('num_seeds', 0)
                num_leeches = info_response[0].get('num_leechs', 0)
                if size > 0:
                    downloaded_percentage = (downloaded / size) * 100
                else:
                    downloaded_percentage = 0
                loading_bar = "▓" * int(downloaded_percentage // 5) + "░" * int(20 - (downloaded_percentage // 5))
                embed_description = (
                    f"Name: **{name}**\n"
                    f"Category: **{category}**\n"
                    f"State: **{state}**\n"
                    f"Size: **{humanize.naturalsize(size, binary=True)}**\n"
                    f"Downloaded: {humanize.naturalsize(downloaded, binary=True)} "
                    f"(**{downloaded_percentage:.2f}%**)\n"
                    f"ETA: **{eta_humanized}**\n\n"
                    f"Progress: **{loading_bar}**"
                )
                footer_text = f"Seeds: {num_seeds} • Peers: {num_leeches}"
                progress_embed.description = embed_description
                progress_embed.set_footer(text=footer_text)
                # Update the existing progress message with the updated embed
                progress_message = await progress_message.edit(embed=progress_embed)
                # Save the movie title when the download is initiated
                if not movie_title:
                    movie_title = name
                    await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name=f"PlexBot API - Downloading: \"{movie_title}\""))
                await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name=f"PlexBot API - Downloading: \"{movie_title}\""))
            await asyncio.sleep(5)  # Add a timed delay of 5 seconds
    except Exception as e:
        print(f"An error occurred: {e}")
        # Reset the flag when an error occurs
        download_in_progress = False
LIBGEN_SEARCH_ROUTE = '/libgen'
LIBGEN_FICTION_SEARCH_ROUTE = '/libgen_fiction_search'
# Emoji for the book embeds
BOOK_EMOJI = '📚'
# Dictionary to store download tasks
download_tasks = {}
def create_book_embed(book):
    # Assuming cover_image is a string containing the URL to the cover image
    embed = discord.Embed(
        title=book['Title'],
        description=(
            f"**Author(s):** {book['Author(s)']}\n" 
            f"**Publisher:** {book['Publisher']}\n"
            f"**Size:** {book['Size']}\n"
            f"**Extension:** {book['Extension']}\n"
            f"**Link:** {book['Link']}"
        ),
        color=0x3498db
    )
    book_cover_image = "https://libgen.is" + book['Image_Link']
    embed.set_image(url=book_cover_image)
    return embed
# Command to search for books

@bot.slash_command(
    name='booksearch',
    description="Search for books",
    option_type=3,
    guild_ids=guilds_list,
    required=True
)
async def booksearch(ctx, query: Option(str, description="Specify a book / research paper", required=True), category: Option(str, description="Specify either Fiction or Nonfiction", required=True, choices=["Non-fiction", "Fiction"])):
    """
    Search for books.
    Parameters:
    - query (str): Specify a book / research paper.
    - category (str): Specify either Fiction or Nonfiction.
    """
    searching_embed = discord.Embed(
        title=f"Searching for {category} text: \"{query}\".",
        description="Please wait while we fetch the results.",
        color=discord.Color.blurple()
    )
    if category is None:
        await ctx.respond("Category must be set!", ephemeral=True)
        return
    if category == 'Fiction':
        search_route = LIBGEN_FICTION_SEARCH_ROUTE
    else:
        search_route = LIBGEN_SEARCH_ROUTE
    initial_message = await ctx.respond(embed=searching_embed, ephemeral=False)
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{API_URL}{search_route}/{query}') as response:
            if response.status != 200:
                await ctx.send(f"Error: Unable to retrieve books. HTTP Status Code: {response.status}")
                return
            books = await response.json()
            for book in books:
                embed = create_book_embed(book)
                embed.set_footer(text=f"React with {BOOK_EMOJI} to download")
                message = await ctx.send(embed=embed)
                await message.add_reaction(BOOK_EMOJI)
                download_tasks[message.id] = book['Link']
# Function to start the download process
async def start_book_download(message, link):
    try:
        # Send a progress embed indicating the download has started
        progress_embed = discord.Embed(
            title="Download in Progress",
            description=f"Downloading from: {link}",
            color=0xffd700
        )
        progress_message = await message.channel.send(embed=progress_embed)
        # Trigger the download API using aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_URL}/libgen_download?link={link}') as response:
                if response.status == 200:
                    download_info = await response.json()
                    if download_info['status'] == 'success':
                        # Send a completion message when the download completes
                        completion_embed = discord.Embed(
                            title="Download Complete",
                            description=f"File saved at: {download_info['final_file_path']}",
                            color=0x00ff00
                        )
                        await progress_message.edit(embed=completion_embed)
                    else:
                        # Send an error message if the download fails
                        error_embed = discord.Embed(
                            title="Download Error",
                            description=f"Error: {download_info['message']}",
                            color=0xff0000
                        )
                        await progress_message.edit(embed=error_embed)
                else:
                    await progress_message.edit(embed=discord.Embed(
                        title="Download Error",
                        description=f"Error: Unable to trigger download. HTTP Status Code: {response.status}",
                        color=0xff0000
                    ))
    except Exception as e:
        # Handle any exceptions that may occur during the download process
        error_embed = discord.Embed(
            title="Download Error",
            description=f"An error occurred: {str(e)}",
            color=0xff0000
        )
        await progress_message.edit(embed=error_embed)

@bot.event
async def on_reaction_add(reaction, user):
    """
    Super important bot event listener that triggers upon reaction.
    """
    consecutive_metadl_responses = 0  
    consecutive_empty_responses = 0
    consecutive_stalleddl_responses = 0
    global download_in_progress  # Declare the global variable
    if user == bot.user:
        return
    if str(reaction.emoji) == BOOK_EMOJI and user.bot is False:
        # Check if the reaction is on a book embed
        if reaction.message.id in download_tasks:
            # Start the download process
            await start_book_download(reaction.message, download_tasks[reaction.message.id])
    if user.id in search_responses:
        data = search_responses[user.id]
        print(f"User {user} reacted with {reaction.emoji} to a message.")
        for item in data:
            #print(f"item fired!")
            if reaction.message.embeds and reaction.message.embeds[0].title == item['title']:
                api_url = f'http://127.0.0.1:5000/selection?url={item["link"]}'
                print(item)
                response = requests.get(api_url).json()
                status = response.get('status', 'Unknown Status')
                color = discord.Color.green() if status == 'Torrent download initiated' else discord.Color.red()
                # Add the green checkmark reaction
                await reaction.message.add_reaction("✅")  # Green checkmark reaction
                # Set the flag to indicate that a download is in progress
                download_in_progress = True
                # Delete other messages sent by the bot in the channel
                async for msg in reaction.message.channel.history(limit=None):
                    if msg.author == bot.user and msg.embeds and msg.id != reaction.message.id:
                        # Check if the embed has a title and it starts with "Torrent download initiated"
                        if msg.embeds[0].title and msg.embeds[0].title.startswith("Download completed") or msg.embeds[0].title.startswith("Movie Suggestion") or msg.embeds[0].title.endswith(")"):
                            continue  # Skip deleting this embed
                        await msg.delete()
                if status == 'Torrent download initiated':
                    while True:
                        if not download_in_progress:
                            break
                        info_global_url = 'http://127.0.0.1:5000/infoglobal'
                        info_response = requests.get(info_global_url).json()
                        # Debugging: Print the info_response
                        print("info_response:", info_response)
                        # Check if the info_response is empty (download is complete)
                        if not info_response:
                            consecutive_empty_responses += 1
                            time.sleep(2) # wtf
                            # Check if we've received 6 consecutive empty responses
                            if consecutive_empty_responses >= 10:
                                # Create a simple embed message to indicate download completion
                                download_complete_embed = discord.Embed(
                                    title=f'Download completed for {item["title"]}!',  # Include the movie title
                                    color=discord.Color.green()
                                )
                                # Send the download complete message
                                await reaction.message.channel.send(embed=download_complete_embed)
                                
                                
                                await bot.change_presence(status=discord.Status.online, activity=None)
                                
                                # Remove the reactions from the user and the bot
                                await reaction.remove(user)
                                try:
                                    await reaction.clear()
                                except discord.errors.NotFound as e:
                                    # Handle the NotFound exception, e.g., log it or ignore it
                                    print(f"Ignored NotFound exception: {e}")
                                except Exception as e:
                                    # Handle other exceptions, if any
                                    print(f"An error occurred: {e}")
                                async for msg in reaction.message.channel.history(limit=None):
                                    if msg.author == bot.user and msg.embeds and msg.embeds[0].title == "Torrent download initiated":
                                        await msg.delete()
                                        break  # Stop searching after the first matching embed is deleted
                                # Break out of the message update loop
                                ctx = await bot.get_context(reaction.message)  # Obtain the context
                                break
                        else:
                            consecutive_empty_responses = 0  # Reset the counter once a response is received
                            
                            # Check if the state contains "MetaDL" indicating a failure to download metadata
                            state = info_response[0].get('state', 'Unknown State')
                            if "metaDL" in state:
                                consecutive_metadl_responses += 1
                                # Check if we've received 30 consecutive MetaDL responses
                                if consecutive_metadl_responses >= 30:
                                    # Create an error embed message to indicate metadata download failure
                                    error_embed = discord.Embed(
                                        title=f'Error: Failed to download metadata for {item["title"]}!',
                                        description=f"The download has encountered repeated metadata download failures. Either the VPN is fucked or the torrent had no peers.",
                                        color=discord.Color.red()
                                    )
                                    # Send the error message and delete the message
                                    await reaction.message.channel.send(embed=error_embed)
                                    await delete(ctx)
                                    # Reset the counters and break out of the loop
                                    consecutive_empty_responses = 0
                                    consecutive_metadl_responses = 0
                                    # Check the status from http://127.0.0.1:5000/infoglobal to see of another download is in progress
                                    url = 'http://127.0.0.1:5000/infoglobal'
                                    response = requests.get(url)
                                    
                                    if response.status_code == 200:
                                        data = response.json()
                                        if data:  # Check if the response is not empty
                                            torrent_name = data[0].get("name", "") # we should NEVER get an empty response here
                                            await bot.change_presence(activity=discord.Game(name=f'qBittorrent API - Downloading: {torrent_name}'), status=discord.Status.idle)
                                        else:
                                            await bot.change_presence(activity=None)
                                    else:
                                        print(f'Error fetching data from {url}') 
                                    break                               
                            else:
                                consecutive_metadl_responses = 0  # Reset the counter for MetaDL responses
                            if "stalledDL" in state:
                                # Increment the counter
                                consecutive_stalleddl_responses += 1
                                # Check if the counter reaches 7200 seconds or 2 hours
                                if consecutive_stalleddl_responses >= 17200:
                                    # Custom message to indicate 100 consecutive "StalledDL" states
                                    error_embed = discord.Embed(
                                        title=f'Error: Download stalled for {item["title"]}!',
                                        description=f"The download has encountered repeated failures to find active peers.",
                                        color=discord.Color.red()
                                    )
                                    # Send the error message and delete the message
                                    await reaction.message.channel.send(embed=error_embed)
                                    # Reset the counter
                                    consecutive_stalleddl_responses = 0
                                    break
                            else:
                                # Reset the counter when "StalledDL" state is not detected
                                consecutive_stalleddl_responses = 0
                        # If the download is still in progress, create an update embed
                        if info_response:
                            category = info_response[0].get('category', '')
                            name = info_response[0].get('name', 'Unknown Name')
                            state = info_response[0].get('state', 'Unknown State')
                            size = info_response[0].get('size', 0)
                            downloaded = info_response[0].get('downloaded', 0)
                            eta_seconds = info_response[0].get('eta', 0)
                            eta_humanized = humanize.naturaldelta(eta_seconds)
                            num_seeds = info_response[0].get('num_seeds', 0)
                            num_leeches = info_response[0].get('num_leechs', 0)
                            dlspeed = info_response[0].get('dlspeed', 0)
                            dlspeed_humanized = humanize.naturalsize(dlspeed, binary=True) + "/s"
                            if not category:
                                category = "Movie"
                            if category =="movie":
                                category = "Movie"
                            if category =="tv":
                                category = "TV"
                            
                            await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name=f"qBittorrent API - Downloading: \"{name}\""))
                            if size > 0:
                                downloaded_percentage = (downloaded / size) * 100
                                # Adjust the progress bar based on download completion
                                loading_bar = "▓" * int(downloaded_percentage // 5) + "░" * int(20 - (downloaded_percentage // 5))
                            else:
                                downloaded_percentage = 0
                                loading_bar = "░" * 20
                            embed_description = (
                                f"Name: {name}\n"
                                f"Category: **{category}**\n"
                                f"State: **{state}**\n"
                                f"Size: **{humanize.naturalsize(size, binary=True)}**\n"
                                f"Downloaded: {humanize.naturalsize(downloaded, binary=True)} "
                                f"**({downloaded_percentage:.2f}%)**\n"
                                f"ETA: **{eta_humanized}**\n\n"
                                f"Progress: {loading_bar} ~{dlspeed_humanized}\n"
                            )
                            footer_text = f"Seeds: {num_seeds} • Peers: {num_leeches}"
                            response_embed = discord.Embed(
                                title=status,
                                color=color
                            )
                            response_embed.description = embed_description
                            response_embed.set_footer(text=footer_text)  # Add footer with seeds and leeches
                            # Edit the message with the updated embed
                            await reaction.message.edit(embed=response_embed)
                            await asyncio.sleep(5)  # Wait for 3 seconds before sending the request again
                # Reset the flag when the download is completed or an error occurs
                download_in_progress = False
                await bot.change_presence(status=discord.Status.online, activity=None)
                
@bot.slash_command(name='pbsdownload', description='Download from PBS given a video URL', guild_ids=guilds_list)
async def pbsdownload(ctx: discord.Interaction, video_url: Option(str, description="Specify a PBS video link", required=True)):
    url_pattern = re.compile(r'(https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z0-9]{2,}(\.[a-zA-Z0-9]{2,})(\.[a-zA-Z0-9]{2,})?')
    if not url_pattern.match(video_url):
        invalid_url_embed = discord.Embed(
            title="Invalid URL",
            description="Please provide a valid URL.",
            color=discord.Color.red()
        )
        await ctx.respond(embed=invalid_url_embed)
        return
    # Assuming Flask server is running on the same machine on port 5000
    flask_endpoint = 'http://127.0.0.1:5000/download_pbs'
    # Prepare the payload for the Flask route
    payload = {
        'video_url': video_url
    }
    # Initial response to indicate that the download has been initiated
    initial_embed = discord.Embed(
        title="PBS download sent for processing",
        description=f"Video URL: {video_url}",
        color=discord.Color.blue()
    )
    initial_response = await ctx.respond(embed=initial_embed)
    await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name=f'PBS API - Downloading {video_url}'))
    try:
        async with aiohttp.ClientSession() as session:
            timeout = aiohttp.ClientTimeout(total=99999) # Dont timeout
            async with session.post(flask_endpoint, json=payload, timeout=timeout) as response:
                if response.status == 200:
                    # Follow-up response on successful download
                    embed_completed = discord.Embed(
                        title=f"PBS download completed",
                        description=f"download completed for: {video_url}",
                        color=discord.Color.green()
                    )
                    await ctx.send(embed=embed_completed)
                    await bot.change_presence(activity=None)
                else:
                    # Follow-up response on error
                    error_message = (await response.json()).get('error', 'Unknown error')
                    embed_error = discord.Embed(
                        title="Error",
                        description=f"An error occurred: {error_message}",
                        color=discord.Color.red()
                    )
                    await initial_response.followup.send(embed=embed_error)
                    await bot.change_presence(activity=None)
    except Exception as e:
        traceback.print_exc()
        await bot.change_presence(activity=None)
        # Follow-up response on unexpected error
        #embed_error = discord.Embed(title="Error",description=f"An unexpected error occurred: {str(e)}",color=discord.Color.red())
        #await initial_response.followup.send(embed=embed_error)
        pass

# Define list of commands
commands_list = [
    "**/search <Movie Title>** - Searches a torrent Search engine API and displays movie results as selectable embeds.",
    "**/altsearch <Movie Title>** - Searches torrent Search engine on yts.mx API and displays movie results as selectable embeds.",
    "**/magnet <Magnet link> <category>** - Manually add a magnet link to the torrent client. Must include either a category",
    "**/delete** - Deletes all torrents and all previous search result embeds.",
    "**/epsearch <TV Show Title>** - Searches for and displays an episode list for each season of a given TV show.",
    "**/tvsearch <TV Show Title SnnEnn>** - Searches a torrent Search engine API and displays TV results as selectable embeds.",
    "**/advtvsearch <Movie Title>** - Searches torrent Search engine on torrentdownload.info and displays TV results as selectable embeds.",
    "**/status** - Shows all active torrents and allows for individual deletion of torrents.",
    "**/stream <query> <media_type> <optional download bool>** - Generate a link to stream any movie or show with an optional argument for basic downloading logic.", #
    "**/youtube <YoutTube title or link>** - Downloads a video from youtube either from a link or through a search.",
    "**/pbsdownload <video_url>** - Download content from pbs.org or any pbs site.", 
    "**/booksearch <title> <fiction/non-fiction>** - Search and download books from libgen.", 
    "**/suggest <Genre>** - Suggests a random movie based on genre by calling an API.",
    "**/diceroll <[optional int]d[int]>** - Rolls dice based on user input and displays result.",
    "**/debug** - Displays debug menu"
]
class CommandSource(menus.ListPageSource):
    def __init__(self, data, per_page=4):
        super().__init__(data, per_page=per_page)
    async def format_page(self, menu, entries):
        page_number = menu.current_page + 1
        total_pages = self.get_max_pages()
        titles = ["Torrent Commands", "Torrent Commands", "Streaming / User Interaction Commands", "User Suggestion Commands", "Misc Debug Commands"]
        
        embed = discord.Embed(
            title=titles[menu.current_page],
            description='\n'.join(entries),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Page {page_number} of {total_pages}")
        return embed
class CustomMenuPages(ui.View, menus.MenuPages):
    def __init__(self, source):
        super().__init__(timeout=60)
        self._source = source
        self.current_page = 0
        self.ctx = None
        self.message = None
    async def start(self, ctx):
        await self._source._prepare_once()
        self.ctx = ctx
        self.message = await self.send_initial_message(ctx, ctx.channel)
    async def _get_kwargs_from_page(self, page):
        value = await super()._get_kwargs_from_page(page)
        if 'view' not in value:
            value.update({'view': self})
        return value
    async def interaction_check(self, interaction):
        return interaction.user == self.ctx.author
    @ui.button(emoji='⏪', style=discord.ButtonStyle.blurple)
    async def first_page(self, button, interaction):
        await self.show_page(0)
        await interaction.response.defer()
    @ui.button(emoji='◀️', style=discord.ButtonStyle.blurple)
    async def before_page(self, button, interaction):
        await self.show_checked_page(self.current_page - 1)
        await interaction.response.defer()
    @ui.button(emoji='▶️', style=discord.ButtonStyle.blurple)
    async def next_page(self, button, interaction):
        await self.show_checked_page(self.current_page + 1)
        await interaction.response.defer()
    @ui.button(emoji='⏩', style=discord.ButtonStyle.blurple)
    async def last_page(self, button, interaction):
        await self.show_page(self._source.get_max_pages() - 1)
        await interaction.response.defer()

@bot.slash_command(name="usage", description="Show a list of available commands", guild_ids=guilds_list,)
async def usage(interaction: discord.Interaction):
    # Create the "Command usage" embed
    initial_embed = discord.Embed(
        title="Command usage has been sent",
        color=discord.Color.blue()
    )
    # Send the initial "Command usage" embed as a response to the slash command
    await interaction.response.send_message(embed=initial_embed, ephemeral=True)
    formatter = CommandSource(commands_list)
    menu = CustomMenuPages(formatter)
    await menu.start(interaction)
    # Use asyncio.sleep to delete the menu message after 60 seconds
    await asyncio.sleep(60)
    await menu.message.delete()

@bot.slash_command(name="suggest", description="Get movie based on genre", guild_ids=guilds_list)
async def suggest(ctx, genre: Option(str, description="Specify the genre for Movie suggestions", required=True, choices=[
    "Action", "Animation", "Biography", "Comedy", "Crime", "Documentary", "Drama", "Family", "Fantasy", "Film-Noir",
    "History", "Horror", "Music", "Musical", "Mystery", "Romance", "Sci-Fi", "Short", "Sport", "Thriller", "War", "Western"
])):
    rating = 0.0  # Initialize rating with a default float value
    accepted_genres = [
        "Action", "Animation", "Biography", "Comedy", "Crime", "Documentary", "Drama", "Family", "Fantasy", "Film-Noir",
        "History", "Horror", "Music", "Musical", "Mystery", "Romance", "Sci-Fi", "Short", "Sport", "Thriller", "War", "Western"
    ]
    # Check if the user requested a random genre
    if genre.lower() == "random":
        # Select a random genre from the list
        genre = random.choice(accepted_genres)
    if genre.lower() not in [g.lower() for g in accepted_genres]:
        genre_list = "\n".join(accepted_genres)
        embed = discord.Embed(title="Invalid Genre", description=f"Please provide a valid genre:\nRandom\n{genre_list}", color=discord.Color.red())
        await ctx.respond(embed=embed, ephemeral=True)
        return
    # Initial response with "Searching for a movie" embed
    search_embed = discord.Embed(title="Searching for a movie", description=f"Searching for a movie in the '{genre}' genre...", color=discord.Color.gold())
    search_message = await ctx.respond(embed=search_embed, ephemeral=False)
    await ctx.trigger_typing()
    genre_lower = genre.lower()
    closest_match = None
    for accepted_genre in accepted_genres:
        if genre_lower in accepted_genre.lower():
            closest_match = accepted_genre
            break
    if closest_match:
        # This indirectly controls how bad recommendations are and directly controls how random recommendations are!
        pages_to_ascend = 6
        scraped_genre = closest_match.lower().replace(" ", "_")
        all_title_link_pairs = []
        def scrape_title_link_pairs(url):
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                links = soup.find_all('a')
                title_link_pairs = []
                for link in links:
                    href = link.get('href')
                    if href and href.startswith('/title') and not href.endswith('/vote'):
                        title = link.text.strip()
                        if title:
                            title_link_pairs.append({"title": title, "link": href})
                return title_link_pairs
            else:
                print("Failed to retrieve the webpage. Status code:", response.status_code)
                return []
        most_recent_suggestion = None  # Initialize a variable to store the most recent suggestion
        suggestion_message_id = None  # Initialize a variable to store the message ID of the current suggestion
        # Read the existing blacklist file line by line into a set, create it if it doesn't exist
        blacklist_set = set()
        # Open the file in append and read mode ('a+')
        with open('blacklist.txt', 'a+') as blacklist_file:
            # Move the file cursor to the beginning for reading
            blacklist_file.seek(0)
            # Read the file line by line
            for line in blacklist_file:
                blacklist_set.add(line.strip())
        while True:
            for page_num in range(pages_to_ascend):
                start_index = page_num * 50 + 1
                current_url = f"https://www.imdb.com/search/title/?title_type=movie&genres={scraped_genre}&start={start_index}&ref_=adv_nxt"
                current_page_title_link_pairs = scrape_title_link_pairs(current_url)
                all_title_link_pairs.extend(current_page_title_link_pairs)
            if all_title_link_pairs:
                random_entry = random.choice(all_title_link_pairs)
                random_entry = random.choice(all_title_link_pairs)
                movie_title = random_entry['title']
                # Check if the movie title is not in the blacklist
                if movie_title not in blacklist_set:
                    # Define 'movie_link' and 'movie_link_with_rating' here
                    movie_link = f"https://www.imdb.com{random_entry['link']}"
                    movie_link_with_rating = f"https://www.imdb.com{random_entry['link']}ratings/?ref_=tt_ov_rt"
                    # Send an HTTP GET request to the URL
                    date_response = requests.get(movie_link, headers=headers)
                    # Check if the request was successful (status code 200)
                    if date_response.status_code == 200:
                        # Parse the HTML content of the page using BeautifulSoup
                        soup = BeautifulSoup(date_response.text, 'html.parser')
                        # Select elements with the CSS selector .sc-5931bdee-1
                        elements = soup.select('ul.ipc-inline-list:nth-child(2) > li:nth-child(1) > a:nth-child(1)')
                        element = None
                        # Loop through the selected elements and extract their text content
                        for element in elements:
                            
                            element = " " + (element.get_text())
                        print("Final element value:", element)
                    else:
                        print(f"Failed to retrieve the page. Status code: {date_response.status_code}")
                    movie_response = requests.get(movie_link_with_rating, headers=headers)
                    if movie_response.status_code == 200:
                        movie_soup = BeautifulSoup(movie_response.text, 'html.parser')
                        # Check for the existence of the .sc-5766672e-1 CSS selector
                        release_date_selector = movie_soup.select('.sc-5766672e-1')
                        if release_date_selector:
                            # This movie has not been released yet, find a new suggestion
                            print("This movie has not been released yet. Finding a new suggestion...")
                            await suggest(ctx, genre=genre)  # Call the suggest command again
                            return
                        # IMDb Rating
                        poster_div = soup.find('div', class_='ipc-media ipc-media--poster-27x40 ipc-image-media-ratio--poster-27x40 ipc-media--baseAlt ipc-media--poster-l ipc-poster__poster-image ipc-media__img')
                        if poster_div:
                            img_tag = poster_div.find('img')
                            if img_tag:
                                poster_link = img_tag['src']
                                print("Poster Link:", poster_link)
                                
                            else:
                                print("Image not found")
                        else:
                            print("Poster div not found")
                        rating_span = soup.find('span', {'class': 'sc-5931bdee-1 jUnWeS'})
                        if rating_span is not None:
                            rating = rating_span.text.strip()
                            # Convert the rating to a float
                            rating = float(rating)
                            embed = discord.Embed(title=random_entry['title'], description=movie_link, color=discord.Color.green())
                            embed.set_footer(text=f"IMDb Rating: {rating}/10")
                        else:
                            embed = discord.Embed(title=random_entry['title'], description=movie_link, color=discord.Color.green())
                            embed.set_footer(text="IMDb Rating: Not available")
                    else:
                        print("Not yet rated. finding new movie")
                        await suggest(ctx, genre=genre)
                        return
                    pattern = re.compile(r'\d+\.\s*')
                    result = pattern.sub('', random_entry['title'])
                    embed = discord.Embed(title=f"{result} ({element.replace(' ', '')})",
                                            description=f"{movie_link}\n\u200B",
                                            color=discord.Color.green())
                    embed.set_image(url=poster_link)
                    # Add clown and pirate flag emoji reactions to the embed
                    message = await ctx.send(embed=embed)
                    await message.add_reaction("🤡")
                    await message.add_reaction("🤖")
                    await message.add_reaction("🏴‍☠️")
                    
                    most_recent_suggestion = random_entry  # Set the most recent suggestion
                    suggestion_message_id = message.id  # Store the ID of the suggestion message
                    print(f"most_recent_suggestion: {most_recent_suggestion}")
                    # Check which emoji was reacted with
                    def check(reaction, user):
                        return (
                            user == ctx.author
                            and reaction.message.id == suggestion_message_id  # Check if the reaction is on the correct message
                            and str(reaction.emoji) in ["🤡", "🏴‍☠️", "🤖"]
                        )
                    start_time = time.time()  # Record the start time for timing purposes
                    reaction, user = await bot.wait_for('reaction_add', check=check)  # Add a timeout for user response
                    end_time = time.time()  # Record the end time for timing purposes
                    print(f"Reaction time: {end_time - start_time} seconds")
                    # Check if a reaction was received
                    if reaction and user:
                        if str(reaction.emoji) == "🤡":
                            if most_recent_suggestion:
                                # Add the movie title to the clown blacklist
                                with open('blacklist.txt', 'a') as clown_blacklist_file:
                                    clown_blacklist_file.write(f"{most_recent_suggestion['title']}\n")
                                await ctx.send(f"{most_recent_suggestion['title']} has been added to the clown blacklist.")
                                most_recent_suggestion = None  # Clear the most recent suggestion
                                await suggest(ctx, genre=genre)
                                break
                            else:
                                await ctx.send("There is no suggestion to add to the blacklist.")
                        elif str(reaction.emoji) == "🏴‍☠️":
                            if most_recent_suggestion:
                                # Add the movie title to the pirate blacklist
                                await search(ctx, search_query=most_recent_suggestion['title'] + element)
                                break
                    # Clear the most recent suggestion after the user's action
                    most_recent_suggestion = None
                else:
                    await ctx.send("Failed to retrieve IMDb and Metacritic ratings.")
            else:
                print("No movie found for the specified genre.")

@bot.slash_command(name="tvsuggest", description="Get TV show suggestions based on genre", guild_ids=guilds_list
)
async def tvsuggest(ctx, genre: str = Option(description="Specify the genre for TV show suggestions", required=True, choices=[
    "Action", "Animation", "Biography", "Comedy", "Crime", "Documentary", "Drama", "Family", "Fantasy", "Game-Show",
    "History", "Horror", "Music", "Musical", "Mystery", "News", "Reality-TV", "Romance", "Sci-Fi", "Sport", "Sport", "Thriller", "War", "Western"
])):
    accepted_genres = [
        "Action", "Animation", "Biography", "Comedy", "Crime", "Documentary", "Drama", "Family", "Fantasy", "Game-Show",
        "History", "Horror", "Music", "Musical", "Mystery", "News", "Reality-TV", "Romance", "Sci-Fi", "Sport", "Sport", "Thriller", "War", "Western"
    ]
    # Check if the user requested a random genre
    if genre.lower() == "random":
        # Select a random genre from the list
        genre = random.choice(accepted_genres)
    if genre.lower() not in [g.lower() for g in accepted_genres]:
        genre_list = "\n".join(accepted_genres)
        embed = discord.Embed(title="Invalid Genre",
                              description=f"Please provide a valid genre:\nRandom\n{genre_list}",
                              color=discord.Color.red())
        await ctx.respond(embed=embed, ephemeral=False)
        return
    await ctx.trigger_typing()
    genre_lower = genre.lower()
    closest_match = None
    for accepted_genre in accepted_genres:
        if genre_lower in accepted_genre.lower():
            closest_match = accepted_genre
            break
    if closest_match:
        pages_to_ascend = 1
        scraped_genre = closest_match.lower().replace(" ", "_")
        # Send an initial message to indicate searching
        search_message = f"Searching for a {genre} suggestion..."
        search_embed = discord.Embed(title="Searching", description=search_message, color=discord.Color.blue())
        await ctx.respond(embed=search_embed, ephemeral=False)
        all_title_link_pairs = []
        def scrape_title_link_pairs(url):
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                links = soup.find_all('a')
                title_link_pairs = []
                for link in links:
                    href = link.get('href')
                    if href and href.startswith('/title') and not href.endswith('/vote'):
                        title = link.text.strip()
                        if title:
                            title_link_pairs.append({"title": title, "link": href})
                return title_link_pairs
            else:
                print("Failed to retrieve the webpage. Status code:", response.status_code)
                return []
        most_recent_suggestion = None  # Initialize a variable to store the most recent suggestion
        suggestion_message_id = None  # Initialize a variable to store the message ID of the current suggestion
        # Read the existing blacklist file line by line into a set
        blacklist_set = set()
        with open('blacklist.txt', 'r') as blacklist_file:
            for line in blacklist_file:
                blacklist_set.add(line.strip())
        while True:
            for page_num in range(pages_to_ascend):
                start_index = page_num * 50 + 1
                current_url = f"https://www.imdb.com/search/title/?title_type=tv_series&genres={scraped_genre}&start={start_index}&ref_=adv_nxt"
                current_page_title_link_pairs = scrape_title_link_pairs(current_url)
                all_title_link_pairs.extend(current_page_title_link_pairs)
            if all_title_link_pairs:
                random_entry = random.choice(all_title_link_pairs)
                movie_title = random_entry['title']
                # Check if the movie title is not in the blacklist
                if movie_title not in blacklist_set:
                    # Define 'movie_link' here
                    movie_link = f"https://www.imdb.com{random_entry['link']}"
                    url = f"https://www.imdb.com{random_entry['link']}"
                    # Send an HTTP GET request to the URL
                    response = requests.get(url, headers=headers)
                    # Check if the request was successful (status code 200)
                    if response.status_code == 200:
                        # Parse the HTML content of the page using BeautifulSoup
                        soup = BeautifulSoup(response.text, 'html.parser')
                        elements = soup.select('div.sc-3a4309f8-0:nth-child(2) > div:nth-child(1) > div:nth-child(1) > a:nth-child(2) > span:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(1) > span:nth-child(1)')
                        # Loop through the selected elements and extract their text content
                        for element in elements:
                            print(element.get_text())
                        else:
                            print(f"Failed to retrieve the page. Status code: {response.status_code}")
                        pattern = re.compile(r'\d+\.\s*')
                        result = pattern.sub('', random_entry['title'])
                        
                        embed = discord.Embed(title=result, description=movie_link,
                                            color=discord.Color.green())
                        embed.set_footer(text=f"IMDb: {element.get_text()}/10")
                        poster_div = soup.find('div', class_='ipc-media ipc-media--poster-27x40 ipc-image-media-ratio--poster-27x40 ipc-media--baseAlt ipc-media--poster-l ipc-poster__poster-image ipc-media__img')
                        if poster_div:
                            img_tag = poster_div.find('img')
                            if img_tag:
                                poster_link = img_tag['src']
                                print("Poster Link:", poster_link)
                                embed.set_image(url=poster_link)
                            else:
                                print("Image not found")
                        else:
                            print("Poster div not found")
                        message = await ctx.respond(embed=embed, ephemeral=False)
                        await message.add_reaction("🤡")
                        await message.add_reaction("🏴‍☠️")
                        most_recent_suggestion = random_entry  # Set the most recent suggestion
                        suggestion_message_id = message.id  # Store the ID of the suggestion message
                        # Check which emoji was reacted with
                        def check(reaction, user):
                            return (
                                user == ctx.author
                                and reaction.message.id == suggestion_message_id  # Check if the reaction is on the correct message
                                and str(reaction.emoji) in ["🤡", "🏴‍☠️"]
                            )
                        start_time = time.time()  # Record the start time for timing purposes
                        reaction, user = await bot.wait_for('reaction_add', check=check)  # Add a timeout for user response
                        end_time = time.time()  # Record the end time for timing purposes
                        print(f"Reaction time: {end_time - start_time} seconds")
                        print(f"emoji selected: {str(reaction.emoji)}")
                        # Check if a reaction was received
                        if str(reaction.emoji) == "🤡":
                            print("emoji selected: 🤡")
                            if most_recent_suggestion:
                                # Add the TV show title to the clown blacklist
                                with open('blacklist.txt', 'a') as clown_blacklist_file:
                                    clown_blacklist_file.write(f"{most_recent_suggestion['title']}\n")
                                await ctx.respond(f"{most_recent_suggestion['title']} has been added to the clown blacklist.", ephemeral=False)
                                most_recent_suggestion = None  # Clear the most recent suggestion
                                await tvsuggest(ctx, genre=genre)
                                break
                            else:
                                await ctx.respond("There is no suggestion to add to the blacklist.", ephemeral=False)
                        elif str(reaction.emoji) == "🏴‍☠️":
                            print("emoji selected: 🏴‍☠️")
                            print(f"most_recent_suggestion: {most_recent_suggestion}")
                            if most_recent_suggestion:
                                print(f"most_recent_suggestion is: {most_recent_suggestion}")
                                # Add the TV show title to the pirate blacklist
                                await tvsearch(ctx, search_query=most_recent_suggestion['title'])
                                break
                            else:
                                await ctx.respond("There is no suggestion to add to the blacklist.", ephemeral=False)
def save_data(data):
    with open('pick_data.txt', 'w') as file:
        file.write('\n'.join(data))
def load_data():
    try:
        with open('pick_data.txt', 'r') as file:
            data = file.read().splitlines()
        return data
    except FileNotFoundError:
        return []
pick_queue = load_data()

@bot.command()
async def pick(ctx, *, text):
    """Add a pick to the queue."""
    pick_queue.append(f"{ctx.author.name}: {text}")
    save_data(pick_queue)
    await ctx.message.add_reaction('✅')

@bot.slash_command(
    name="diceroll",
    description="Roll a dice with with a supplied number of sides",
    guild_ids=guilds_list
)
async def diceroll(
    ctx, 
    die_value: Option(int, description="Number of sides on the dice.", required=True),
    multiplier: Option(int, description="Number of dice (optional)", required=False)
):
    try:
        if multiplier is None:
            multiplier = 1
        # Roll the dice
        rolls = [random.randint(1, die_value) for _ in range(multiplier)]
        total = sum(rolls)
        # Create an embed to display the results
        embed = discord.Embed(title="Dice Roll", description=f"{ctx.author.name} rolled {multiplier}d{die_value}")
        embed.add_field(name="Rolls", value=", ".join(map(str, rolls)))
        embed.add_field(name="Total", value=total)
        # Respond with the embed as a direct response to the slash command
        await ctx.respond(embed=embed, ephemeral=False)
    except Exception as e:
        await ctx.respond("Invalid dice expression. Please use the format `/diceroll <required die value> <optional int multiplier>`", ephemeral=True)

@bot.slash_command(name="simplebooksearch",
            description="Search for direct download links of books or research papers on annas-archive.org.",
            option_type=3,
            guild_ids=guilds_list,
            required=True
            )
async def booksearch(ctx, query: Option(str, description="Specify the title or keywords of the book or research paper to search on annas-archive.org", required=True)):
    initsearch_embed = discord.Embed(
            title=f"Searching for the book/paper:  '{query}'",
            color=discord.Color.blue()
        )
    await ctx.respond(embed=initsearch_embed)
    # Make a request to the Flask app with the search query
    response = requests.get(f'http://127.0.0.1:5000/books?search={query}')
    data = response.json()
    # Display the top 5 results in Discord embeds
    for book in data['books'][:5]:
        embed = discord.Embed(title=book['title'], description=book['details'], color=discord.Color.blue())
        embed.set_thumbnail(url=book['img_url'])
        # Add download links to the embed
        for download_link in book['download_links']:
            embed.add_field(name=download_link['option'], value=download_link['url'], inline=False)
        embed.add_field(name="More Info", value=f"[Book Details]({book['link']})", inline=False)
        await ctx.send(embed=embed)

@bot.slash_command(
    name="pdfdownload",
    description="Download a pdf file from a direct download link.",
    guild_ids=guilds_list
)
async def pdf_download(ctx, download_link: Option(str, description="Specify a direct download link for a .pdf .epub or any similar human file.", required=True), filename: Option(str, description="Specify the name to save the file without a file extension", required=True)):
    """
    Download a file from a direct download link.
    Parameters:
    - url (str): The direct download link.
    - filename (str): The desired file name.
    Returns:
    - str: A message indicating whether the download was successful or failed.
    """
    try:
        initsearch_embed = discord.Embed(
            title=f"Download initiated for the book/paper: '{filename}'",
            color=discord.Color.blue()
        )
        await ctx.respond(embed=initsearch_embed)
        
        response = requests.get(download_link, stream=True)
        response.raise_for_status()
        # Use a local temporary directory
        temp_dir = os.path.join(os.getcwd(), "Temp")
        # Create the directory if it doesn't exist
        os.makedirs(temp_dir, exist_ok=True)
        # Extract file extension from the download link
        parsed_url = urlparse(download_link)
        file_extension = parsed_url.path.split('.')[-1]
        # Add the file extension to the filename in the temporary directory
        temp_filename = os.path.join(temp_dir, f"{filename}.{file_extension}")
        with open(temp_filename, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
        # Move the file to the network share after the download is complete
        Drive_or_path = config.get('Storage', 'Books_save_path').replace('\\','/')
        final_filename = os.path.join(f"{Drive_or_path}", f"{filename}.{file_extension}")
        shutil.move(temp_filename, final_filename)
        embed = discord.Embed(
            title=f"Download Successful for {final_filename}!",
            description=f"The file is now being sent to [books.serverboi.org](https://books.serverboi.org/#library_id=Library&panel=book_list).",
            color=discord.Color.green()
        )
    except requests.exceptions.RequestException as e:
        embed = discord.Embed(
            title=f"Download Failed for {filename}",
            description=f"Error: {e}",
            color=discord.Color.red()
        )
    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)
    await ctx.send(embed=embed)
bot_token = config.get('Bot', 'token')
bot.run(bot_token)
