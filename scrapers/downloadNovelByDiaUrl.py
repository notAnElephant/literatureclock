import logging
import os
import re
import time

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def sanitize_filename(name):
    """Removes invalid characters for filenames and replaces spaces."""
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return name.replace(" ", "_")


# --- Configuration ---

# The "pretty" public-facing URL of the book you want to download
INITIAL_URL = "https://reader.dia.hu/document/Zavada_Pal-A_fenykepesz_utokora-7871/"

# The directory where the final merged .xhtml file will be saved
DOWNLOAD_DIR = "../dia_downloads"

# ---------------------

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



# Get domain/base URL and Ebook ID from the initial URL
try:
    BASE_DOMAIN = INITIAL_URL.split('/')[2]
    BASE_URL = "https://" + BASE_DOMAIN

    # Extract the Ebook ID (e.g., '7871') from the URL
    id_match = re.search(r'-(\d+)/?$', INITIAL_URL)
    if not id_match:
        raise ValueError("Could not extract Ebook ID (e.g., -7871) from INITIAL_URL.")
    EBOOK_ID = id_match.group(1)
    logging.info(f"Extracted Ebook ID: {EBOOK_ID}")

except (IndexError, ValueError) as e:
    logging.error(f"Invalid INITIAL_URL: {e}")
    exit(1)


def get_file_list_with_selenium(driver, initial_url):
    """
    Uses Selenium to load the page, wait for the redirect, and then
    injects JavaScript to call the API and get the file list.
    """
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
    api_url = f"{BASE_URL}/rest/epub-reader/init-setting/"

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
    full_urls = [BASE_URL + path for path in component_paths]

    # --- Filter out the unwanted file ---
    # Example filter pattern: 'PIMDIA7871_szerzoseg'
    filter_pattern = f"PIMDIA{EBOOK_ID}_szerzoseg"
    logging.info(f"Filtering out files matching: *{filter_pattern}*")

    filtered_urls = [url for url in full_urls if filter_pattern not in url]

    logging.info(f"Proceeding with {len(filtered_urls)} files after filtering.")

    # We also need the browser's cookies to download the files
    browser_cookies = driver.get_cookies()

    return filtered_urls, browser_cookies, final_url, author, title


def download_and_merge_files(file_urls, browser_cookies, referer_url, final_filename, author, title):
    """
    Downloads each file, cleans unwanted tags, parses its <body>,
    and merges them all into a single HTML file.
    """
    logging.info(f"Downloading {len(file_urls)} files to merge into '{final_filename}'...")

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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
        logging.info(f"Downloading & parsing file {i + 1}/{len(file_urls)}: {filename}")

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

            time.sleep(0.1)  # Be polite

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

    save_path = os.path.join(DOWNLOAD_DIR, final_filename)

    try:
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(final_html)
        logging.info(f"\n--- Merge complete! ---")
        logging.info(f"Successfully saved merged file to: {save_path}")
    except IOError as e:
        logging.error(f"Failed to write final merged file: {e}")


def main():
    """
    Main function to run the entire download process using Selenium.
    """
    driver = None
    try:
        logging.info("Setting up Selenium WebDriver...")
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Run in background
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--window-size=1920,1080')
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.set_script_timeout(30)

        # Step 1: Get file list, cookies, and metadata
        file_urls, browser_cookies, referer_url, author, title = get_file_list_with_selenium(driver, INITIAL_URL)

        # Step 2: Create the safe filename
        safe_author = sanitize_filename(author)
        safe_title = sanitize_filename(title)
        final_filename = f"{safe_author}_{safe_title}.xhtml"

        # Step 3: Download and merge all files into one
        download_and_merge_files(file_urls, browser_cookies, referer_url, final_filename, author, title)

    except Exception as e:
        logging.error(f"\n--- An error occurred ---")
        logging.error(e)
    finally:
        if driver:
            logging.info("Closing browser.")
            driver.quit()


if __name__ == "__main__":
    main()

