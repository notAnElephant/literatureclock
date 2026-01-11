import logging
import os
import re
import time
import json
import argparse
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


# --- Configuration ---
DEFAULT_DOWNLOAD_DIR = "../dia_downloads"

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def sanitize_filename(name):
    """Removes invalid characters for filenames and replaces spaces."""
    name = re.sub(r'[\\/*?:\"<>|]', "", name)
    return name.replace(" ", "_")


def extract_url_info(url):
    """
    Extracts the base URL and Ebook ID from the given URL.
    Returns (base_url, ebook_id) or raises ValueError.
    """
    try:
        # e.g. https://reader.dia.hu/document/...
        parts = url.split('/')
        if len(parts) < 3:
             raise ValueError("URL too short to extract domain.")
        
        base_domain = parts[2]
        base_url = "https://" + base_domain

        # Extract the Ebook ID (e.g., '7871') from the URL
        # Matches -1234 at the end of the string, optional slash
        id_match = re.search(r'-(\d+)/?$', url)
        if not id_match:
            raise ValueError(f"Could not extract Ebook ID (e.g., -7871) from URL: {url}")
        
        ebook_id = id_match.group(1)
        return base_url, ebook_id

    except (IndexError, ValueError) as e:
        raise ValueError(f"Invalid URL format '{url}': {e}")


def get_file_list_with_selenium(driver, initial_url):
    """
    Uses Selenium to load the page, wait for the redirect, and then
    injects JavaScript to call the API and get the file list.
    """
    base_url, ebook_id = extract_url_info(initial_url)
    logging.info(f"Processing ID: {ebook_id} from {initial_url}")

    logging.info(f"Navigating to initial URL: {initial_url}")
    driver.get(initial_url)

    # Wait for the browser to be redirected to the URL with the token
    try:
        wait = WebDriverWait(driver, 20)  # Wait up to 20 seconds
        wait.until(EC.url_contains("token="))
    except Exception as e:
        logging.error(f"Page did not redirect to a URL with a token. Timed out. {e}")
        raise

    final_url = driver.current_url
    logging.info(f"Redirected to final URL: {final_url}")

    # Now that we are on the page with a valid session, we can
    # inject JavaScript to call the API ourselves.
    api_url = f"{base_url}/rest/epub-reader/init-setting/"

    script = f"""
    var callback = arguments[arguments.length - 1];
    fetch('{api_url}', {{
        headers: {{
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': '{final_url}'
        }}
    }})
    .then(response => response.ok ? response.json() : Promise.reject('API response was not ok'))
    .then(data => callback({{success: true, data: data}}))
    .catch(err => callback({{success: false, error: err.message || err}}));
    """

    logging.info(f"Injecting JavaScript to call API: {api_url}")

    try:
        result = driver.execute_async_script(script)
    except Exception as e:
        logging.error(f"Error executing injected JavaScript: {e}")
        raise

    if not result.get('success'):
        raise Exception(f"Injected JavaScript failed: {result.get('error')}")

    json_data = result.get('data')

    # --- Extract Metadata ---
    meta_data = json_data.get("metaData", {})
    author = meta_data.get("author", "UnknownAuthor").strip()
    title = meta_data.get("title", "UnknownTitle").strip()
    logging.info(f"Found metadata: Title='{title}', Author='{author}'")

    # Parse the JSON data from the API
    component_paths = json_data.get("view", {}).get("components", [])
    if not component_paths:
        raise ValueError("API response did not contain 'view.components' list.")

    logging.info(f"Found {len(component_paths)} total components in API response.")

    # Convert relative paths to full URLs
    full_urls = [base_url + path for path in component_paths]

    # --- Filter out the unwanted file ---
    # Example filter pattern: 'PIMDIA7871_szerzoseg'
    filter_pattern = f"PIMDIA{ebook_id}_szerzoseg"
    logging.info(f"Filtering out files matching: *{filter_pattern}*")

    filtered_urls = [url for url in full_urls if filter_pattern not in url]

    logging.info(f"Proceeding with {len(filtered_urls)} files after filtering.")

    # We also need the browser's cookies to download the files
    browser_cookies = driver.get_cookies()

    return filtered_urls, browser_cookies, final_url, author, title

def download_and_merge_files(file_urls, browser_cookies, referer_url, final_filename, author, title, download_dir):
    """
    Downloads each file, cleans unwanted tags, parses its <body>,
    and merges them all into a single HTML file.
    """
    os.makedirs(download_dir, exist_ok=True)
    save_path = os.path.join(download_dir, final_filename)
    
    if os.path.exists(save_path):
        logging.info(f"File already exists: {save_path}. Skipping.")
        return

    logging.info(f"Downloading {len(file_urls)} files to merge into '{final_filename}'...")

    session = requests.Session()
    for cookie in browser_cookies:
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

    session.headers.update({
        'Accept': 'application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': referer_url,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })

    all_bodies = []  # To store the inner HTML of each file's body

    for i, url in enumerate(file_urls):
        filename = url.split('/')[-1]
        # logging.debug(f"Downloading & parsing file {i + 1}/{len(file_urls)}: {filename}")

        try:
            response = session.get(url)
            response.raise_for_status()

            # Parse the XHTML content
            soup = BeautifulSoup(response.content, "lxml")

            # Find the <body> tag
            body = soup.find("body")

            if body:
                # --- START: Remove unwanted tags (New) ---

                # Remove <a name="DIAPage..."> tags
                # We use a regex in the 'name' attribute search
                for a_tag in body.find_all("a", {"name": re.compile(r"DIAPage\d+"), "shape": "rect"}):
                    a_tag.decompose()  # Remove the tag completely

                # Remove <span class="oldaltores">...</span> tags
                for span_tag in body.find_all("span", class_="oldaltores"):
                    span_tag.decompose()  # Remove the tag completely

                # --- END: Remove unwanted tags ---

                # Extract the *inner content* of the cleaned body tag
                all_bodies.append(body.decode_contents())
            else:
                logging.warning(f"Could not find <body> tag in {filename}")

            time.sleep(0.05)  # Be polite but fast

        except requests.exceptions.RequestException as e:
            logging.warning(f"Failed to download {url}: {e}")
        except Exception as e:
            logging.warning(f"Failed to parse {url}: {e}")

    if not all_bodies:
        logging.error("No content was successfully parsed. Aborting merge.")
        return

    logging.info("All files parsed. Merging content...")

    # --- Create the final merged HTML file ---

    # Join all body contents, separated by a horizontal rule for readability
    merged_content = "<br><hr><br>".join(all_bodies)

    # Create a simple HTML5 wrapper for the merged content
    final_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <title>{title}</title>
    <style>
        /* Basic styling for readability */
        body {{ 
            font-family: 'Georgia', serif; 
            line-height: 1.6; 
            max-width: 800px; 
            margin: 2rem auto; 
            padding: 2rem;
            background-color: #fdfdfd;
            color: #1a1a1a;
        }}
        h1, h2 {{ 
            font-family: 'Helvetica', 'Arial', sans-serif;
            font-weight: 300;
            border-bottom: 1px solid #ccc;
            padding-bottom: 10px;
        }}
        h1 {{ font-size: 2.5rem; }}
        h2 {{ font-size: 1.8rem; color: #555; }}
        hr {{ 
            border: 0;
            height: 1px;
            background: #ddd;
            margin: 2rem 0;
        }}
        /* Styles from the ebook content will be applied as-is */
    </style>
</head>
<body>
    <h1>{title}</h1>
    <h2>{author}</h2>

    {merged_content}

</body>
</html>
"""

    try:
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(final_html)
        logging.info(f"Successfully saved merged file to: {save_path}")
    except IOError as e:
        logging.error(f"Failed to write final merged file: {e}")

def process_url(driver, url, download_dir):
    try:
        logging.info(f"--- Starting process for: {url} ---")
        # Step 1: Get file list, cookies, and metadata
        file_urls, browser_cookies, referer_url, author, title = get_file_list_with_selenium(driver, url)

        # Step 2: Create the safe filename
        safe_author = sanitize_filename(author)
        safe_title = sanitize_filename(title)
        final_filename = f"{safe_author}_{safe_title}.xhtml"

        # Step 3: Download and merge all files into one
        download_and_merge_files(file_urls, browser_cookies, referer_url, final_filename, author, title, download_dir)

    except Exception as e:
        logging.error(f"Failed to process URL {url}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Download and merge DIA books from URLs.")
    parser.add_argument("url", nargs="?", help="The URL of the book to download (e.g. https://reader.dia.hu/document/ப்புகளை")
    parser.add_argument("--all", action="store_true", help="Download all books listed in ../dia_downloads/_summary.json")
    parser.add_argument("--output", default=DEFAULT_DOWNLOAD_DIR, help=f"Directory to save downloads (default: {DEFAULT_DOWNLOAD_DIR})")

    args = parser.parse_args()

    # Locate the summary file relative to the script
    script_dir = Path(__file__).parent.resolve()
    # Default location for the summary file if not specified otherwise (used with --all)
    summary_path = script_dir.parent / 'dia_downloads' / '_summary.json'

    urls_to_process = []

    if args.url:
        urls_to_process.append(args.url)
    
    if args.all:
        if not summary_path.exists():
            logging.error(f"Summary file not found at {summary_path}. Run dia_scraper.py first.")
            sys.exit(1)
        
        try:
            logging.info(f"Reading URLs from {summary_path}...")
            with open(summary_path, 'r', encoding='utf-8') as f:
                # Can be pure JSON or the python dict string (if not yet fixed)
                # But we expect valid JSON now as per the fix in dia_scraper.py
                # To be safe, we can try json.load.
                data = json.load(f)
                
                # Flatten the dictionary of lists
                # data format: {"Author Name": ["url1", "url2"], ...}
                for author, links in data.items():
                    urls_to_process.extend(links)
            
            logging.info(f"Found {len(urls_to_process)} URLs in summary file.")
            
        except json.JSONDecodeError:
            logging.error(f"Failed to decode JSON from {summary_path}. Is it valid JSON?")
            sys.exit(1)
        except Exception as e:
            logging.error(f"Error reading summary file: {e}")
            sys.exit(1)

    if not urls_to_process:
        print("No URLs to process. Provide a URL argument or use --all.")
        parser.print_help()
        sys.exit(0)

    # Setup Driver once
    driver = None
    try:
        logging.info("Setting up Selenium WebDriver...")
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--window-size=1920,1080')
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.set_script_timeout(30)

        total = len(urls_to_process)
        for i, url in enumerate(urls_to_process):
            logging.info(f"[{i+1}/{total}] Processing: {url}")
            process_url(driver, url, args.output)

    except Exception as e:
        logging.error(f"\n--- An error occurred in main loop ---")
        logging.error(e)
    finally:
        if driver:
            logging.info("Closing browser.")
            driver.quit()


if __name__ == "__main__":
    main()