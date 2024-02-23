import configparser
import os
import re
import requests
import shutil
import subprocess
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from qbittorrent import Client
from pytube import YouTube
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from urllib.parse import quote, urlparse, urljoin, urlunparse
from youtube_search import YoutubeSearch
import yt_dlp

# Load the initial configuration
config = configparser.ConfigParser()
config.read('config.ini')

qb_host = config.get('qbit', 'host')
qb = Client(qb_host)
qb_user = config.get('qbit', 'user')
qb_pass = config.get('qbit', 'pass')
# Inital login
qb.login(qb_user, qb_pass) 
app = Flask(__name__)

async def login_command(): 
    try:

        qb.login(qb_user, qb_pass) 
        print('qb session refreshed!')
    except Exception as e:
        print(f"An error occurred during qb login: {e}")
        print(f"An error occurred during qb login: {str(e)}")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
}

@app.route('/')
def index():
    return 'Bot backend is running'

@app.route('/api/config', methods=['POST'])
def update_config():
    try:
        new_config = request.form.to_dict(flat=False)
        for key, value in new_config.items():
            section, option = key.split('|')
            config.set(section, option, value[0])

        with open('config.ini', 'w') as configfile:
            config.write(configfile)

        return jsonify({'message': 'Config updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def convert_url_format(url):
    # Replace any subdomain that starts with "video." with "www.pbs.org"
    converted_url = re.sub(r'https://video\.(.*?)/', r'https://www.pbs.org/', url)
    
    # Extract video title from the URL (you may need to adjust this based on the video URL structure)
    video_title_match = re.search(r'/video/([^/]+)/', converted_url)
    video_title = video_title_match.group(1) if video_title_match else 'unknown_title'
    
    return converted_url, video_title

@app.route('/download_pbs', methods=['POST'])
def download_pbs():
    data = request.json

    if 'video_url' not in data:
        return jsonify({"error": "Missing 'video_url' parameter"}), 400

    video_url = data['video_url']

    try:
        # Convert the URL format
        converted_url, video_title = convert_url_format(video_url)

        # Define download options for video only
        ydl_opts_video = {
            'format': 'bestvideo/best',
            'outtmpl': f'temp/{video_title}_video.%(ext)s',
        }

        # Download video stream
        with yt_dlp.YoutubeDL(ydl_opts_video) as ydl_video:
            result = ydl_video.extract_info(converted_url, download=True)

            # Check if a separate audio stream is available
            if 'formats' in result and any(format_info.get('acodec') != 'none' for format_info in result['formats']):
                print("Separate audio stream found. Skipping audio download and merge.")
                # Use subprocess to call ffmpeg for merging and append "_final" to the file name
                ffmpeg_command = (
                    f'ffmpeg -i "temp/{video_title}_video.mp4" -c copy "temp/{video_title}_final.mp4"'
                )
                subprocess.run(ffmpeg_command, shell=True)

                PBS_location = config.get('Storage', 'PBS_save_path')
                # Move final merged file to destination
                final_destination = f'{PBS_location}'
                shutil.move(f'temp/{video_title}_final.mp4', os.path.join(final_destination, f'{video_title}_final.mp4'))

            else:
                # If no separate audio stream, proceed with regular flow
                PBS_location = config.get('Storage', 'PBS_save_path')
                # Move video file to destination without appending "_final"
                final_destination = f'{PBS_location}'
                shutil.move(f'temp/{video_title}_video.mp4', os.path.join(final_destination, f'{video_title}_video.mp4'))

            # Remove the contents of the downloads folder
            shutil.rmtree('temp')
            # Recreate the downloads folder
            os.makedirs('temp')

            return jsonify({"message": f"PBS Download Completed for {video_title}"}), 200

    except yt_dlp.DownloadError as e:
        # Handle download errors
        print(f"Download error: {str(e)}")
        return jsonify({"error": f"An error occurred during download: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"An error occurred during download: {str(e)}"}), 500

def click_element(driver, element):
    try:
        driver.execute_script("arguments[0].click();", element)
    except Exception as e:
        print(f"Error clicking element: {str(e)}")

def get_imdb_url(title):
    encoded_title = quote(title)
    return f"https://www.imdb.com/find/?q={encoded_title}&s=tt&ttype=tv&ref_=fn_tv"

def get_episode_names(driver, season_url):
    driver.get(season_url)

    # Check for the presence of the error message
    error_message = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="empty-message"] p[data-testid="main-message"]')
    if error_message:
        print("No more seasons found.")
        return []

    # Wait for the episodes to load
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'article.sc-f1a948e3-1 h4 div a div')))
    except Exception as e:
        print(f"Error waiting for episodes to load: {str(e)}")

    # Extract episode names
    episode_elements = driver.find_elements(By.CSS_SELECTOR, 'article.sc-f1a948e3-1 h4 div a div')
    episode_names = [episode.text for episode in episode_elements]

    while True:
        # Check if there is a "N More" button
        more_button = driver.find_elements(By.CSS_SELECTOR, 'span.ipc-see-more:nth-child(1) > button:nth-child(1)')
        if not more_button:
            break  # No more episodes to load, exit the loop

        try:
            # Scroll to the "N More" button
            ActionChains(driver).move_to_element(more_button[0]).perform()

            # Wait for the "N More" button to be clickable
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'span.ipc-see-more:nth-child(1) > button:nth-child(1)')))

            # Click the "N More" button using JavaScript
            click_element(driver, more_button[0])

            # Wait for the newly loaded episodes to be present in the DOM
            WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'article.sc-f1a948e3-1 h4 div a div')))

            # Extract the additional episode names
            additional_episode_elements = driver.find_elements(By.CSS_SELECTOR, 'article.sc-f1a948e3-1 h4 div a div')
            additional_episode_names = [episode.text for episode in additional_episode_elements]

            # If no additional episodes are found, exit the loop
            if not additional_episode_names:
                break

            # Extend the original episode names list with the new episodes
            episode_names.extend(additional_episode_names)

        except Exception as e:
            print(f"Error waiting for/clicking 'N More' button: {str(e)}")
            break

    return episode_names

@app.route('/episodes')
def search_episodes():
    title = request.args.get('title')
    selection = request.args.get('selection')

    if not title:
        return "Please provide a 'title' parameter in the URL query."

    # Default selection to None if not provided
    if selection is None:
        selection = -1
    else:
        try:
            selection = int(selection)
        except ValueError:
            return "Invalid 'selection' parameter. It should be an integer."

    imdb_url = get_imdb_url(title)

    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        driver = webdriver.Chrome(options=chrome_options)  # You may need to adjust the path to your WebDriver executable
        driver.get(imdb_url)

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        episode_info = []

        first_url_element = soup.select_one("li.ipc-metadata-list-summary-item:nth-child(1) > div:nth-child(2) > div:nth-child(1) > a:nth-child(1)")
        second_url_element = soup.select_one("li.ipc-metadata-list-summary-item:nth-child(2) > div:nth-child(2) > div:nth-child(1) > a:nth-child(1)")
        third_url_element = soup.select_one("li.ipc-metadata-list-summary-item:nth-child(3) > div:nth-child(2) > div:nth-child(1) > a:nth-child(1)")

        url_elements = [first_url_element, second_url_element, third_url_element]

        for index, url_element in enumerate(url_elements):
            if url_element:
                episode_url = f"https://www.imdb.com{url_element.get('href')}"
                episode_title = url_element.get_text()
                episode_info.append({"title": episode_title, "url": episode_url})

        if episode_info:
            if selection == -1:
                # If no selection is provided, return the TV show details and season URLs
                return jsonify({"show_info": episode_info})
            elif 0 <= selection < len(episode_info):
                selected_url = episode_info[selection]["url"]
                # Extract the TV show ID from the URL
                tv_show_id = selected_url.split('/')[4]
                season_urls = [f'https://www.imdb.com/title/{tv_show_id}/episodes/?season={season}' for season in range(1, 999)]  # Assuming up to 999 maximum seasons 
                episode_names = []

                for season_url in season_urls:
                    # Check if "N More" button is present before trying to click
                    more_button = driver.find_elements(By.CSS_SELECTOR, 'span.ipc-see-more:nth-child(1) > button:nth-child(1)')
                    if more_button:
                        try:
                            # Scroll to the "N More" button
                            ActionChains(driver).move_to_element(more_button[0]).perform()

                            # Wait for the "N More" button to be clickable
                            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'span.ipc-see-more:nth-child(1) > button:nth-child(1)')))

                            # Click the "N More" button using JavaScript
                            click_element(driver, more_button[0])
                        except Exception as e:
                            print(f"Error waiting for/clicking 'N More' button: {str(e)}")

                    episode_names.extend(get_episode_names(driver, season_url))

                    # Check for the presence of the error message after loading episodes
                    error_message = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="empty-message"] p[data-testid="main-message"]')
                    if error_message:
                        print("No more seasons found. Breaking out of the loop.")
                        break

                return jsonify({"show_info": episode_info, "episode_names": episode_names})

            else:
                return "Invalid 'selection' index. It should be within the range of available episodes."
        else:
            return "No episode URLs found on IMDb for the given title."
    except Exception as e:
        return f"An error occurred: {str(e)}"
    finally:
        driver.quit()
import cloudscraper
# List of 1337x mirrors with '*' indicating CloudScraper usage
mirrors = [

    "https://www.1337xx.to/",
    "https://www.1377x.to/",
    "https://1337x.unblockit.foo/", # This one and down are mirrors ran by the public
    "https://www.1337xxx.to/",
    "https://www.1337x.tw",
    "https://1337xto.to/",
    "https://1337x.st/",
    "https://x1337x.ws/"
]

def make_request(url, headers=None):
    # Use CloudScraper for URLs behind cloudflare bot protection
    if any(url.startswith(mirror) for mirror in ["https://x1337x.ws/", "https://1337x.unblockninja.com/", "https://1337x.st/", "https://x1337x.se/", "https://x1337x.ws/"]):
        print(f"Scraping with cloudscraper: {url}")
        scraper = cloudscraper.create_scraper()
        if headers:
            return scraper.get(url, headers=headers)
        return scraper.get(url)
    else:
        print(f"Scraping with requests: {url}")
        if headers:
            return requests.get(url, headers=headers)
        return requests.get(url)

@app.route('/torrents', methods=['GET'])
def get_torrents():
    search = request.args.get('search', 'spiderman')

    for mirror in mirrors:
        try:
            target_url = f"{mirror}category-search/{search}/Movies/1/"
            response = make_request(target_url)

            if response.status_code == 200:
                break  # Stop trying mirrors if a successful response is received

        except RequestException as e:
            # Handle request exceptions and try the next mirror
            print(f"Request exception for mirror {mirror}: {str(e)}")
            continue

    if response.status_code == 403:
        return jsonify({"error": "Reauthentication failed"}), 403

    html = response.text
    soup = BeautifulSoup(html, 'html.parser')

    torrents = []

    parsed_url = urlparse(target_url)
    base_link = f"{parsed_url.scheme}://{parsed_url.netloc}"

    rows = soup.find_all('tr')

    for index, row in enumerate(rows):
        if index >= 5:  # Limit the loop to the first 5 results
            break

        title_column = row.select_one('.coll-1.name a:nth-of-type(2)')
        if title_column:
            title = title_column.get_text()
            link = title_column['href']
            full_link = f"{base_link}{link}"

            seeds_column = row.select_one('.coll-2.seeds')
            seeds = seeds_column.get_text() if seeds_column else "N/A"

            leeches_column = row.select_one('.coll-3.leeches')
            leeches = leeches_column.get_text() if leeches_column else "N/A"

            size_column = row.select_one('.coll-4.size')
            size_span = size_column.select_one('span')
            if size_span:
                size_span.extract()
            size = size_column.get_text().strip() if size_column else "N/A"

            # Scrape image from the linked page
            image_src = scrape_image(full_link)

            torrent_info = {
                "title": title,
                "link": full_link,
                "seeds": seeds,
                "leeches": leeches,
                "size": size,
            }

            if image_src:
                torrent_info["cover_image_url"] = f'https://1337xx.to{image_src}'

            torrents.append(torrent_info)

    return jsonify(torrents)

def scrape_image(link):
    response = make_request(link)
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')

    image_div = soup.select_one('.torrent-image-wrap img')
    if image_div:
        return image_div['src']

    return None

def format_season_episode(query):
    # Define a regular expression pattern to match "SXEY" where X and Y are numbers
    pattern = r'S(\d{1,2})E(\d{1,2})'
    match = re.search(pattern, query)
    
    if match:
        season = match.group(1).zfill(2)  # Format as "S01"
        episode = match.group(2).zfill(2)  # Format as "E01"
        formatted_query = re.sub(pattern, f'S{season}E{episode}', query)
    else:
        formatted_query = query
        season = "00"  # Default season value
        episode = "00"  # Default episode value
    
    return formatted_query

@app.route('/tv', methods=['GET'])
def get_tv_torrents():
    search = request.args.get('search', 'spiderman')
    formatted_query = format_season_episode(search)
    print({formatted_query})
    
    mirrors = [
        #"https://www.1337x.to/", This mirror's img cdn is acting up
        "https://www.1337xx.to/",
        "https://www.1377x.to/",
        "https://1337x.unblockit.foo/", # This one and down are mirrors ran by the public
        "https://www.1337xxx.to/",
        "https://www.1337x.tw",
        "https://1337xto.to/",
        "https://1337x.st/",
        "https://x1337x.ws/"
    ]
    

    
    torrents = []
    
    for mirror in mirrors:
        try:
            target_url = f"{mirror}category-search/{formatted_query}/TV/1/"
            response = make_request(target_url, headers)
    

    
            if response.status_code == 200:
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')
    
                parsed_url = urlparse(target_url)
                base_link = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
                rows = soup.find_all('tr')
    
                for index, row in enumerate(rows):
                    if index >= 5:  # Limit the loop to first 5 results
                        break
                    
                    title_column = row.select_one('.coll-1.name a:nth-of-type(2)')
                    if title_column:
                        title = title_column.get_text()
                        link = title_column['href']
                        full_link = f"{base_link}{link}"
    
                        seeds_column = row.select_one('.coll-2.seeds')
                        seeds = seeds_column.get_text() if seeds_column else "N/A"
    
                        leeches_column = row.select_one('.coll-3.leeches')
                        leeches = leeches_column.get_text() if leeches_column else "N/A"
    
                        size_column = row.select_one('.coll-4.size')
                        size_span = size_column.select_one('span')
                        if size_span:
                            size_span.extract()
                        size = size_column.get_text().strip() if size_column else "N/A"
    
                        # Scrape image from the linked page
                        image_src = scrape_image(full_link)
    
                        torrent_info = {
                            "title": title,
                            "link": full_link,
                            "seeds": seeds,
                            "leeches": leeches,
                            "size": size,
                        }
    
                        if image_src:
                            torrent_info["cover_image_url"] = f'https:{image_src}'
                        
                        torrents.append(torrent_info)
    
                break  # Stop trying mirrors if successful
    
        except RequestException as e:
            # Handle request exceptions and try the next mirror
            print(f"Request exception for mirror {mirror}: {str(e)}")
    
    return jsonify(torrents)

def scrape_with_selenium(search_query):
    try:
        # Set up Chrome WebDriver with headless option
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        driver = webdriver.Chrome(options=chrome_options)

        # Construct the URL with the search query
        url = f'https://anybt.eth.limo/#/search?q={search_query}&order=&category=&s=tgo'

        # Load the webpage
        driver.get(url)

        # Wait for the content to be available (adjust wait time as needed)
        wait = WebDriverWait(driver, 10)
        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.title-flex.title')))

        # Extract the text
        title_text = element.text

        # Close the WebDriver
        driver.quit()

        return title_text

    except Exception as e:
        return str(e)

# Define the base URL
BASE_URL = "https://www.torrentdownload.info"

@app.route('/advtv', methods=['GET'])
def advtv():
    # Get the search query from the URL parameter "search"
    search_query = request.args.get('search')

    if not search_query:
        return jsonify({"error": "Search query is missing."}), 400

    # Build the URL with the search query
    search_url = f"https://www.torrentdownload.info/searchr?q={search_query}"

    # Send an HTTP GET request to the URL
    response = requests.get(search_url)

    if response.status_code == 200:
        # Parse the HTML content of the page
        soup = BeautifulSoup(response.text, 'html.parser')

        # Use CSS selector to find all search result elements
        result_elements = soup.select('td.tdleft')

        # Determine the number of results to print (up to 5 or the available results)
        num_results_to_print = min(len(result_elements) - 3, 5)

        if num_results_to_print <= 0:
            return jsonify([]), 200

        # Extract and store the results in a list
        results = []
        for i, result in enumerate(result_elements[3:3 + num_results_to_print], start=4):
            title_element = result.find('div', class_='tt-name').find('a')
            title = title_element.text
            relative_link = title_element['href']

            # Prepend the base URL to the relative link
            link = BASE_URL + relative_link

            results.append({"Result": f"{title}", "Link": link})

        # Get the "selection" query parameter to determine the index of the selected result
        selection = request.args.get('selection')
        if selection is not None:
            try:
                selection_index = int(selection)
                if 1 <= selection_index <= num_results_to_print:
                    # Send a request to the selected result's link
                    selected_link = results[selection_index - 1]['Link']
                    response = requests.get(selected_link)
                    if response.status_code == 200:
                        # Parse the selected result's page to find the magnet link
                        selected_soup = BeautifulSoup(response.text, 'html.parser')
                        magnet_link_element = selected_soup.select_one('span.bigtosa a.tosa[href^="magnet:"]')
                        magnet_link = magnet_link_element['href'] if magnet_link_element else "Magnet link not found"

                        # Extract seeds and leeches information
                        seeds_and_leeches = selected_soup.select('td.td-min b:contains("Peers:")')
                        if seeds_and_leeches:
                            seeds_and_leeches_text = seeds_and_leeches[0].find_next('td').get_text()
                            seeds_match = re.search(r'Seeds: (\d+)', seeds_and_leeches_text)
                            leeches_match = re.search(r'Leechers: (\d+)', seeds_and_leeches_text)

                            seeds = int(seeds_match.group(1)) if seeds_match else 0
                            leeches = int(leeches_match.group(1)) if leeches_match else 0
                        else:
                            seeds = 0
                            leeches = 0

                        # Extract size information
                        size_element = selected_soup.select_one('td.td-min b:contains("Size:")')
                        size = size_element.find_next('td').get_text() if size_element else "Size not found"

                        return jsonify([{
                            "magnet": magnet_link,
                            "title": results[selection_index - 1]['Result'],
                            "link": selected_link,
                            "seeds": seeds,
                            "leeches": leeches,
                            "size": size
                        }]), 200
                else:
                    return jsonify({"error": "Invalid selection index."}), 400
            except ValueError:
                return jsonify({"error": "Invalid selection index."}), 400

        return jsonify({"results": results}), 200

    else:
        return jsonify({"error": "Failed to retrieve search results.", "status_code": response.status_code}), 500  


        
# List of YTS mirrors sorted by availability
yts_mirrors = [
    "https://yts.mx/",
    "https://ytss.mx/",
    "https://yts.rs/",
    "https://yts.unblockit.foo",
    "https://yts.am/", #This one and down are just redirections 
    "https://yts.rs/",
    "https://yts.lt/",
    "https://yts.ag/"
]

@app.route('/torrents-yts', methods=['GET'])
def get_movie_info():
    movie_title = request.args.get('search')
    movie_urls, mirror_used = find_movie_on_mirrors(movie_title)

    if movie_urls == ["Movie not found on YTS."]:
        return jsonify([{"error": "Movie not found on YTS"}])

    results = []
    for movie_url in movie_urls:
        try:
            magnet_link, image_link, title = get_magnet_link_seeds_size_cover(movie_url)
            result = {
                "mirror_used": mirror_used,
                "cover_image_url": image_link,
                "leeches": "NA",
                "link": movie_url,
                "seeds": "NA",
                "size": "NA",
                "title": title
            }
            results.append(result)
        except Exception as e:
            continue  # Optionally log this error

    return jsonify(results)

def find_movie_on_mirrors(movie_title):
    for mirror in yts_mirrors:
        try:
            movie_url = get_movie_url(movie_title, mirror)
            if movie_url != "Movie not found on YTS.":
                return movie_url, mirror
        except RequestException:
            continue
    return "Movie not found on YTS.", "No mirrors available"

def get_movie_url(movie_title, mirror):
    movie_title_url = movie_title.replace(' ', '-').lower()
    url = f"{mirror}browse-movies/{movie_title_url}/all/all/0/likes/0/all"

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        movie_links = soup.find_all('a', class_='browse-movie-link', limit=5)
        return [link['href'] for link in movie_links if link] if movie_links else ["Movie not found on YTS."]
    return ["Movie not found on YTS."]

def get_magnet_link_seeds_size_cover(url):
    # Start a new instance of the Chrome web browser
    chrome_options = Options()
    chrome_options.add_experimental_option('prefs', {
        'download.prompt_for_download': False,
        'download.directory_upgrade': True,
        'safebrowsing.enabled': True
    })
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode (no visible browser window)
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # Set the browser window size
        driver.set_window_size(1920, 1080)  # Adjust the size as needed

        # Open the YTS movie URL
        driver.get(url)

        try:
            img_element = driver.find_element(By.CSS_SELECTOR, ".img-responsive")
            image_link = img_element.get_attribute("src")
            

            
        except Exception as e:
            image_link = None

        element = driver.find_element(By.CSS_SELECTOR, "div.hidden-xs:nth-child(1) > h1:nth-child(1)")

        # Extract the text content of the element
        title = element.text

        # Print the text
        print("Title:", title)


        # Locate the button element by its class
        button = driver.find_element(By.CLASS_NAME, "torrent-modal-download")

        # Interact with the button by clicking it
        button.click()

        try:
            # Find the first <a> element with the specified title
            element = driver.find_element(By.CSS_SELECTOR, 'a[title*="1080p Magnet"]')

            # Extract the href attribute of the element
            magnet_link = element.get_attribute("href")
        except Exception as e:
            magnet_link = None

        return magnet_link, image_link, title

    except Exception as e:
        raise

@app.route('/selection', methods=['GET'])
async def get_selection():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}, 400)

    category = ""  # Initialize the category variable

    if url.startswith("magnet:"):
        # If the URL is a magnet link, send it to the torrent client with "tv" as the category
        await login_command()
        qb.download_from_link(url, category="tv")
        return jsonify({"status": "Torrent download initiated"})

    if url.startswith("https://yts.mx"):
        # New logic for YTS URL
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return jsonify({"error": str(e)}, 400)

        # Parse the YTS page using BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the magnet link with a title including "1080p"
        magnet_link = None
        for a in soup.select('a.magnet-download'):
            if '1080p' in a['title'].lower():
                magnet_link = a['href']
                break

        if magnet_link:
            # Download the torrent using qBittorrent API
            await login_command()
            qb.download_from_link(magnet_link)
            return jsonify({"status": "Torrent download initiated"})
        else:
            return jsonify({"error": "Magnet link with '1080p' title not found"}, 404)

    else:
        # Previous logic for non-YTS URL (e.g., if URL doesn't match any specific pattern)
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return jsonify({"error": str(e)}, 400)

        html = response.text

        # Attempt to select the element using the first CSS selector
        first_css_selector = 'ul:nth-child(2) > li:nth-child(1) > span:nth-child(2)'
        element = BeautifulSoup(html, 'html.parser').select_one(first_css_selector)

        if element:
            # Extract the text from the element
            category_text = element.get_text().strip()

            # Check if the extracted text is "TV" and set the category accordingly
            if category_text.lower() == "tv":
                category = "tv"
            else:
                category = "movie"
        else:
            category = "tv"

        # Find the magnet link using a regular expression
        magnet_link_pattern = re.compile(r'magnet:\?xt=urn:btih:[a-zA-Z0-9]+')
        magnet_link_match = re.search(magnet_link_pattern, html)

        if magnet_link_match:
            magnet_link = magnet_link_match.group()

            # Download the torrent using qBittorrent API (implement your download logic)
            await login_command()
            qb.download_from_link(magnet_link, category=category)

            return jsonify({"status": "Torrent download initiated"})
        else:
            return jsonify({"error": "Magnet link not found"}, 404)

@app.route('/setcategory', methods=['GET'])
async def set_category():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 400

    soup = BeautifulSoup(response.text, 'html.parser')

    category_span = soup.select('.l784f2d88ae608bfadc444c26ab129ffd12a484c8 > ul:nth-child(2) > li:nth-child(1) > span')

    if category_span:
        category_text = category_span[0].text.strip()
        if category_text == "TV":
            infohash_span = soup.select('.infohash-box > p:nth-child(1) > span:nth-child(2)')
            if infohash_span:
                infohash = infohash_span[0].text.strip()
                await login_command()
                qb.set_category(infohash, "TV")
                return jsonify({"status": f"Category set to 'TV' for infohash: {infohash}"})
    
    return jsonify({"status": "No action taken"})

@app.route('/info', methods=['GET'])
async def get_torrent_info():
    infohash = request.args.get('infohash')
    if not infohash:
        return jsonify({"error": "Missing 'infohash' parameter"}), 400

    try:
        await login_command()
        torrent_info = qb.get_torrent(infohash)

        if torrent_info:
            return jsonify(torrent_info)
        else:
            return jsonify({"error": "Torrent not found"}), 404
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": str(e)}), 404

async def delete_permanently(infohash_list):
    await login_command()
    qb.delete_permanently(infohash_list)

@app.route('/delete/<infohash>', methods=['DELETE'])
def delete_file(infohash):
    try:
        # Call delete_permanently with the provided infohash
        delete_permanently(infohash)
        return jsonify({'message': 'File deleted successfully.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#delete all
@app.route('/delete', methods=['GET'])
async def delete_torrents_route():
    try:
        await login_command()
        torrents = qb.torrents()
        for torrent in torrents:
            qb.delete_all()
        
        # If deletion is successful, return a success message
        return jsonify({'message': 'All torrents deleted successfully.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/spellcheck', methods=['GET'])
def spellcheck():
    # Get the 'search' query parameter from the URL
    search_query = request.args.get('search')

    # Ensure the 'search' query parameter is provided
    if not search_query:
        return jsonify({'error': 'The "search" query parameter is required'}), 400

    # Construct the IMDb API URL
    imdb_api_url = f'https://v3.sg.media-imdb.com/suggestion/x/{search_query}.json'

    # Send a GET request to the IMDb API
    response = requests.get(imdb_api_url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        movie_data = data.get('d', [])

        # Extract movie titles and create a list of formatted movie information
        movie_info = [{'title': movie['l'], 'year': movie['y'], 'cast': movie.get('s', 'N/A')} for movie in movie_data if 'y' in movie]

        return jsonify(movie_info)
    else:
        return jsonify({'error': 'Failed to fetch data from IMDb API'}), 500

@app.route('/getipaddr', methods=['GET'])
def before_first_request():
    ip = get('https://api.ipify.org').content.decode('utf8')

    print('My public IP address is: {}'.format(ip))
    return jsonify('{}'.format(ip))

@app.route('/infoglobal', methods=['GET'])
async def get_filtered_torrents():
    try:
        # Define your filter parameters based on your requirements
        filters = {
            'filter': 'downloading',  # Current status of the torrents
            'sort': 'time_active',           # Sort torrents by ratio
            'limit': 10,               # Limit the number of torrents returned
            'offset': 0               # Set offset (if needed)
        }
        await login_command()
        torrent_list = qb.torrents(**filters)

        if isinstance(torrent_list, list):
            return jsonify(torrent_list)
        else:
            return jsonify({"error": "Torrent list not available"}), 404
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": str(e)}), 404

download_url = None
download_progress = 0
download_in_progress = False

# Set the download path
YT_path = config.get('Storage', 'YT_save_path')
download_path = YT_path.replace('\\','/')

def download_video(video_url):
    global download_progress, download_in_progress

    try:
        yt = YouTube(video_url, on_progress_callback=progress_callback)
        stream = yt.streams.get_highest_resolution()

        # Replace invalid characters in the video title with underscores
        invalid_characters = r'<>:"/\|?*'
        cleaned_title = ''.join(c if c.isalnum() or c in [' ', '.', '-', '_'] else '_' for c in yt.title if c not in invalid_characters)

        # Remove consecutive spaces and strip leading/trailing spaces
        cleaned_title = ' '.join(cleaned_title.split())

        # Set the download path
        download_file_path = os.path.join(download_path, f'{cleaned_title}.mp4')

        # Start the download
        stream.download(output_path=download_path, filename=f'{cleaned_title}.mp4')

        # Reset flags when download completes
        download_in_progress = False
        download_progress = 0

        return cleaned_title  # Return the cleaned title for demonstration purposes
    except Exception as e:
        return str(e)
def progress_callback(stream, chunk, bytes_remaining):
    global download_progress

    # Your custom logic for progress reporting
    download_progress = int((1 - bytes_remaining / stream.filesize) * 100)
    print(f'Download progress: {download_progress}%')

# New route to get the current download progress
@app.route('/progress', methods=['GET'])
def get_download_progress():
    global download_in_progress, download_progress

    if download_in_progress:
        return jsonify({'status': 'success', 'progress_percentage': download_progress})

    return jsonify({'status': 'error', 'message': 'No active download'})

@app.route('/download', methods=['GET'])
def download():
    global download_url, download_progress, download_in_progress

    video_url = request.args.get('url')

    if video_url:
        if 'youtube.com' in video_url and 'watch?v=' in video_url:
            # Provided URL is a valid YouTube video link
            download_url = video_url
        else:
            # Perform a search if the provided input is not a direct YouTube video URL
            results = YoutubeSearch(video_url, max_results=1).to_dict()
            if results:
                selected_video = results[0]
                url_suffix = selected_video['url_suffix']

                # Clean the video URL
                download_url = f'https://youtube.com{url_suffix}'
            else:
                return jsonify({'status': 'error', 'message': 'No search results found'})

        # Set download flags and initiate the download
        download_progress = 0
        download_in_progress = True

        title = download_video(download_url)
        return jsonify({'status': 'success', 'download_url': download_url, 'title': title, 'progress_percentage': download_progress})

    return jsonify({'status': 'error', 'message': 'No video URL provided'})
@app.route('/search', methods=['GET'])
def search_and_download():
    global download_url, download_progress, download_in_progress

    search_term = request.args.get('q')
    max_results = int(request.args.get('max_results', 10))
    selection_index = int(request.args.get('index', -1))

    results = YoutubeSearch(search_term, max_results=max_results).to_dict()

    if 0 <= selection_index < len(results):
        selected_video = results[selection_index]
        url_suffix = selected_video['url_suffix']

        # Clean the video URL
        video_url = url_suffix

        # Set the download URL
        download_url = f'https://youtube.com{video_url}'
        download_progress = 0
        download_in_progress = True

        title = download_video(download_url)
        return jsonify({'status': 'success', 'download_url': download_url, 'title': title, 'progress_percentage': download_progress})

    # If no selection index is provided, return the list of search results
    return jsonify({'status': 'success', 'results': results})

def download_video(video_url):
    global download_progress, download_in_progress

    try:
        yt = YouTube(video_url, on_progress_callback=progress_callback)
        stream = yt.streams.get_highest_resolution()

        # Replace invalid characters in the video title with underscores
        invalid_characters = r'<>:"/\|?*'
        cleaned_title = ''.join(c if c.isalnum() or c.isspace() or c in ['.', '-', '_'] else '_' for c in yt.title if c not in invalid_characters).replace('_','')

        # Set the download path
        download_file_path = os.path.join(download_path, f'{cleaned_title}.mp4')

        # Start the download
        stream.download(output_path=download_path, filename=f'{cleaned_title}.mp4')

        # Reset flags when download completes
        download_in_progress = False
        download_progress = 0

        return cleaned_title.strip()  # Return the cleaned title for demonstration purposes
    except Exception as e:
        return str(e)

def progress_callback(stream, chunk, bytes_remaining):
    global download_progress

    # Your custom logic for progress reporting
    download_progress = int((1 - bytes_remaining / stream.filesize) * 100)
    print(f'Download progress: {download_progress}%')

def download_file(video_src, media_name, folder):
    # Create the folder if it doesn't exist
    if not os.path.exists(folder):
        os.makedirs(folder)

    # Extract the file extension from the URL
    file_extension = video_src.split(".")[-1].split("?")[0]

    # Set the file path in the project directory
    local_file_path = os.path.join(folder, f"{media_name}.{file_extension}")

    # Download the file
    response = requests.get(video_src, stream=True)
    with open(local_file_path, 'wb') as file:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                file.write(chunk)

    print(f"File downloaded to {local_file_path}")

    # Move the file to the network path
    move_file_to_network(local_file_path, video_src)

def move_file_to_network(local_file_path, video_link):
    # Specify the network path based on the video link
    if "tv_mp4" in video_link:
        TV_save_path = config.get('Storage', 'TV_save_path').replace('\\','/')
        network_path = TV_save_path
    elif "movie_mp4" in video_link:
        movies_save_path = config.get('Storage', 'Movies_save_path').replace('\\','/')
        network_path = movies_save_path
    else:
        print("Unknown file type.")
        return

    # Create the network folder if it doesn't exist
    if not os.path.exists(network_path):
        os.makedirs(network_path)

    # Set the destination path in the network folder
    network_file_path = os.path.join(network_path, os.path.basename(local_file_path))

    # Move the file to the network path
    shutil.move(local_file_path, network_file_path)
    print(f"File moved to {network_file_path}")
    


# List of mirrors to try
MIRRORS = ["https://annas-archive.org/", "https://annas-archive.gs", "https://annas-archive.se"]

def get_available_mirror():
    for mirror in MIRRORS:
        try:
            # Check if the mirror is responding to HEAD requests
            response = requests.head(mirror)
            if response.status_code == 200:
                return mirror
        except requests.RequestException:
            continue
    return None

@app.route('/books', methods=['GET'])
def scrape_books():
    # Get the search argument from the query parameters
    search_query = request.args.get('search')
    # Get the index argument from the query parameters
    index_param = request.args.get('index')


    # Check if the search query is provided
    if not search_query:
        return jsonify({'error': 'Search query parameter is required'}), 400

    # Find an available mirror
    base_url = get_available_mirror()

    if not base_url:
        return jsonify({'error': 'No available mirrors'}), 500

    print(f"Using mirror: {base_url}")

    # Create a CloudScraper instance
    scraper = cloudscraper.create_scraper()

    # URL to scrape with the provided search query
    url = f"{base_url}/search?index=&q={search_query}&src=zlib&sort="

    print(f"Scraping URL: {url}")

    # Make a GET request and parse the HTML content
    response = scraper.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all the div elements with class "h-[125] flex flex-col justify-center"
    results = soup.find_all('div', class_='h-[125] flex flex-col justify-center')[:5]

    # Initialize a list to store the results
    book_results = []

    # Iterate through the results and extract information
    for index, result in enumerate(results):
        # Extract the link
        link_element = result.find('a')
        link = f"{base_url}" + link_element['href'] if link_element else "Link not found"

        print(f"Processing book {index + 1}: {link}")

        # Extract other details like title, format, author, etc.
        title_element = result.find('h3', class_='max-lg:line-clamp-[2] lg:truncate leading-[1.2] lg:leading-[1.35] text-md lg:text-xl font-bold')
        title = title_element.text.strip() if title_element else "Title not found"

        details_element = result.find('div', class_='truncate leading-[1.2] lg:leading-[1.35] max-lg:text-xs')
        details = details_element.text.strip() if details_element else "Details not found"

        # Extract the image URL
        img_element = result.find('img', class_='relative inline-block')
        img_url = img_element['src'] if img_element and 'src' in img_element.attrs else "Image URL not found"

        # Make another request to the book link to get download links
        book_response = scraper.get(link)
        book_soup = BeautifulSoup(book_response.text, 'html.parser')

        # Extract download links for "Slow Partner Server" or specific titles only
        download_links = []
        download_elements = book_soup.find_all('a', class_='js-download-link')
        for download_element in download_elements:
            option_text = download_element.text.strip()
            if 'Slow Partner Server' in option_text or option_text.startswith('Libgen.li'):
                download_links.append({
                    'option': option_text,
                    'url': f"{base_url}" + download_element['href']

                })
                for item in download_links:
                    if item['url'].startswith('https://annas-archive.org/http://libgen.li/'):
                        #remove the base url if needed
                        cleanedurl = item['url'].replace('https://annas-archive.org/','')
                        item['url'] = cleanedurl

        # Append the results to the list
        book_result = {
            'index': index + 1,
            'title': title,
            'link': link,
            'details': details,
            'img_url': img_url,
            'download_links': download_links
        }

        # Include the book result only if the index matches the specified index_param
        if not index_param or int(index_param) == (index + 1):
            book_results.append(book_result)

    # Return the results as JSON
    return jsonify({'books': book_results})

# List of libgen mirrors
lib_mirrors = [
    'https://libgen.rs/',
    'https://libgen.is/',
    'https://libgen.st/',
    'http://90.156.207.33/',
    'http://178.33.94.116/',
    'http://91.229.23.48/',
    'http://141.148.234.41/'
]

def scrape_libgen(search_query):
    # Set up the Selenium WebDriver
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    data = []

    for mirror in lib_mirrors:
        # URL for Libgen search with the provided query
        url = f"{mirror}search.php?req={search_query}&lg_topic=libgen&open=0&view=simple&res=25&phrase=1&column=def"

        # Create a new WebDriver for each mirror
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to the Libgen search page
        driver.get(url)

        try:
            # Wait for the table to load
            table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'table.c'))
            )

            # Extract data from each row, limited to 5 results
            for row in table.find_elements(By.TAG_NAME, 'tr')[1:]:
                # Extract the link from the third column
                links = row.find_elements(By.CSS_SELECTOR, 'td:nth-child(3) a')
                book_link = next((link.get_attribute('href') for link in links if '/book' in link.get_attribute('href')), None)
                link = book_link or links[0].get_attribute('href')

                # Extract other columns
                columns = row.find_elements(By.TAG_NAME, 'td')
                row_data = [col.text.strip() for col in columns]

                # Include the link in the data
                row_data.append(link)

                # Extract image link for the current book
                image_link = extract_libgen_image_link(link)
                row_data.append(image_link)

                data.append(dict(zip(["ID", "Author(s)", "Title", "Publisher", "Year", "Pages", "Language", "Size", "Extension", "Mirrors", "Mirrors", "Edit", "Link", "Image_Link"], row_data)))

                # Break the loop if 5 results are collected
                if len(data) == 5:
                    return data

        except Exception as e:
            print(f"Mirror {mirror} failed with error: {str(e)}")
        finally:
            # Close the WebDriver
            driver.quit()

    return data

def extract_libgen_image_link(url):
    try:
        # Fetch the HTML content of the given URL
        response = requests.get(url)
        response.raise_for_status()

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Specify the CSS selector to locate the image link
        css_selector = 'td[width="240"] > a > img'

        # Extract the image link using the specified CSS selector
        img_element = soup.select_one(css_selector)

        # Check if the element is found before accessing its attributes
        if img_element:
            image_link = img_element.get('src')
            return image_link
        else:
            print(f"Image element not found on {url}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching content from {url}: {e}")
        return None
    except Exception as e:
        print(f"Error extracting image link: {e}")
        return None

@app.route('/libgen/<search_query>', methods=['GET'])
def libgen(search_query):
    result = scrape_libgen(search_query)
    return jsonify(result)
from urllib.parse import urlparse, unquote
def download_book_from_mirror(link, lib_mirror):
    base_url = f'{lib_mirror}book/index.php?md5='
    print(f"Book base url: {base_url}")
    link = link.replace(base_url, 'http://library.lol/main/')
    print(f"Link: {link}")

    # Set up a headless Chrome browser using Selenium
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    browser = webdriver.Chrome(options=chrome_options)

    try:
        # Make a request to the final download page
        browser.get(link)
        final_download_link = browser.find_element(By.CSS_SELECTOR, '#download a').get_attribute('href')

        # Extract original filename and extension from the download link
        parsed_url = urlparse(final_download_link)
        original_filename = unquote(os.path.basename(parsed_url.path))

        # Download the file to a temporary directory in the project
        temp_dir = os.path.join(os.getcwd(), 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, original_filename)

        with requests.get(final_download_link, stream=True) as response:
            with open(temp_file_path, 'wb') as temp_file:
                shutil.copyfileobj(response.raw, temp_file)

        # Move the downloaded file to the network share set in config.ini
        Drive_or_path = config.get('Storage', 'Books_save_path').replace('\\','/')
        network_share_dir = Drive_or_path
        os.makedirs(network_share_dir, exist_ok=True)
        final_file_path = os.path.join(network_share_dir, original_filename)
        shutil.move(temp_file_path, final_file_path)

        return {'status': 'success', 'final_file_path': final_file_path}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
    finally:
        # Close the browser
        browser.quit()

@app.route('/libgen_download', methods=['GET'])
def libgen_download():
    link = request.args.get('link', '')
    
    for mirror in lib_mirrors:
        result = download_book_from_mirror(link, mirror)
        if result['status'] == 'success':
            return jsonify(result)
    
    return jsonify({'status': 'error', 'message': 'All mirrors failed'})

def extract_libgen_book_info(soup):
    # Extract book information from the detailed page
    cover_image = soup.find('img', alt='cover')['src']
    title = soup.find('td', class_='record_title').text.strip()

    authors_elem = soup.find_all('a', href=lambda x: x and '/?q=' in x)
    authors = [author.text.strip() for author in authors_elem]

    series_elem = soup.find('td', class_='field', string='Series:')
    series = series_elem.find_next('td').text.strip() if series_elem else None

    language_elem = soup.find('td', class_='field', string='Language:')
    language = language_elem.find_next('td').text.strip() if language_elem else None

    publisher_elem = soup.find('td', class_='field', string='Publisher:')
    publisher = publisher_elem.find_next('td').text.strip() if publisher_elem else None

    isbn_elem = soup.find('td', class_='field', string='ISBN:')
    isbn = isbn_elem.find_next('td').text.strip() if isbn_elem else None

    format_elem = soup.find('td', class_='field', string='Format:')
    file_format = format_elem.find_next('td').text.strip() if format_elem else None

    size_elem = soup.find('td', class_='field', string='File size:')
    file_size = size_elem.find_next('td').text.strip() if size_elem else None

    id_elem = soup.find('td', class_='field', string='ID:')
    book_id = id_elem.find_next('td').text.strip() if id_elem else None

    # Extract download links
    download_links_elem = soup.select('ul.record_mirrors li a')
    download_links = [a['href'] for a in download_links_elem]

    # Extract book description
    description_elem = soup.find('td', class_='field', string='Description:')
    description = description_elem.find_next('td').text.strip() if description_elem else None

    book_info = {
        'Image_Link': cover_image,
        'Title': title,
        'Author(s)': authors,
        'Series': series,
        'Language': language,
        'Publisher': publisher,
        'ISBN': isbn,
        'Extension': file_format,
        'Size': file_size,
        'Book_ID': book_id,
        'Link': download_links[0] if download_links else None,
        'Description': description,
    }

    return book_info

@app.route('/libgen_fiction_search/<search_query>')
def libgen_fiction_search(search_query):
    for mirror in lib_mirrors:
        base_url = f'{mirror}fiction/'
        search_url = f'{base_url}?q={search_query}&criteria=&language=English&format='

        try:
            response = requests.get(search_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            catalog_table = soup.find('table', class_='catalog')
            if catalog_table:
                books = []

                # Limit the loop to the first 5 books
                for row in catalog_table.find_all('tr')[1:6]:
                    columns = row.find_all('td')
                    title_column = columns[2]
                    title_link = title_column.find('a')

                    if title_link:
                        book_url = f"{base_url.rstrip('/')}/{title_link['href'].lstrip('/')}".replace('/fiction/fiction', '/fiction')
                        print(book_url)

                        # Secondary request to get detailed information
                        book_response = requests.get(book_url)
                        book_response.raise_for_status()

                        book_soup = BeautifulSoup(book_response.text, 'html.parser')
                        book_info = extract_libgen_book_info(book_soup)

                        books.append(book_info)

                return jsonify(books)
            else:
                return jsonify({'error': 'No results found'})
        except requests.RequestException as e:
            print(f'Request failed for mirror {mirror}: {str(e)}')
            continue  # Try the next mirror in case of an error

    return jsonify({'error': 'All mirrors failed'})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
