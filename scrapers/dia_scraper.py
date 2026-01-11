import re
import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def get_all_author_names():
    """
    Fetches all author names from the main DIA page.
    (This function is fast, so requests is fine here)
    """
    print("Fetching all author names...")
    response = requests.get('https://dia.hu/')
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    author_names = []
    for link in soup.select('a.authors-block--author'):
        author_names.append(link.text)
    print(f"Found {len(author_names)} authors.")
    return author_names


def parse_works_from_page(page_source, author_name):
    """
    Parses the works from a given HTML page source.
    (This is your original dia_scraper, modified to accept HTML)
    """
    soup = BeautifulSoup(page_source, 'html.parser')
    urls = []

    # Determine surname for filtering
    # If "Apollinaire, Guillaume" -> "Apollinaire"
    # If "Ady Endre" -> "Ady"
    target_surname = author_name.split(',')[0].strip().split()[0].lower()

    for record in soup.select('div.data-wrapper-opus'):
        # Filter by author name to avoid including works where the author is just a translator/subject
        record_text = record.get_text(strip=True)
        # Format usually "Author Name: Title"
        parts = record_text.split(':', 1)
        if parts:
            record_author = parts[0].strip().lower()
            # Simple check: does the surname appear in the record's author field?
            if target_surname not in record_author:
                # logging.debug(f"Skipping work by '{parts[0]}' (target: '{author_name}')")
                continue

        # Extract epubId from /record/-/record/PIMDIAxxxx
        link = record.select_one('a[href*="PIMDIA"]')
        if not link:
            continue

        m = re.search(r'PIMDIA(\d+)', link['href'])
        if not m:
            continue
        epub_id = m.group(1)

        # Find the preceding hidden span with the component name
        comp_div = record.find_previous('div', class_='data-wrapper-space')
        if not comp_div:
            continue
        hidden_span = comp_div.select_one('span[style*="display:none"]')
        if not hidden_span:
            continue
        component = hidden_span.text.strip()

        # Clean component: remove the trailing ID (e.g. -03790) if present
        # Example: Ady_Endre-Ady_Endre_osszes_versei-03790 -> Ady_Endre-Ady_Endre_osszes_versei
        clean_component = re.sub(r'-\d+$', '', component)

        url = f'https://reader.dia.hu/document/{clean_component}-{epub_id}'
        urls.append(url)

    print(f'Found {len(urls)} reader URLs on this page (after filtering).')
    return urls


def get_all_works_for_author(driver, author_name):
    """
    Gets all works for a given author using Selenium to navigate and click.
    """
    all_works = []
    initial_url = f'https://resolver.pim.hu/dia/muvek/"{author_name}"'

    try:
        driver.get(initial_url)
    except Exception as e:
        print(f"Error navigating to initial URL for {author_name}: {e}")
        return []

    page_num = 1
    while True:
        print(f"Scraping page {page_num} for {author_name}...")
        try:
            # Wait for the list of works OR the pagination controls to be present
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.data-wrapper-opus, p.pager"))
            )
        except TimeoutException:
            if page_num == 1:
                print(f"No works found on the first page for {author_name}. Skipping.")
            else:
                print("Timed out waiting for new page content. Assuming end of pages.")
            break  # Stop if no works are found (or on timeout)

        # Parse the works from the current page
        works_on_page = parse_works_from_page(driver.page_source, author_name)
        # If no works on page 1, we'll just let the "next button" check fail
        if not works_on_page and page_num == 1:
            print("No works found on page 1 (or all filtered out).")

        all_works.extend(works_on_page)

        try:
            # Find the "Next" button based on the icon class you provided
            next_button_icon = driver.find_element(By.CSS_SELECTOR, "p.pager i.fa-angle-right")
            # Get the parent <button> element
            next_button = next_button_icon.find_element(By.XPATH, "parent::button")

            # Check if the button is disabled
            if "disabled" in next_button.get_attribute("class"):
                print("Next button is disabled. Reached the last page.")
                break

            # Capture an element from the current page to check for staleness
            try:
                current_content = driver.find_element(By.CSS_SELECTOR, "div.data-wrapper-opus")
            except NoSuchElementException:
                current_content = None

            # If not disabled, click it to go to the next page
            print("Clicking 'Next' button...")
            driver.execute_script("arguments[0].click();", next_button)
            
            # Wait for the page to update
            if current_content:
                try:
                    WebDriverWait(driver, 10).until(EC.staleness_of(current_content))
                except TimeoutException:
                    print("Timed out waiting for page update (staleness). Proceeding anyway...")

            # Wait for new content to load
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.data-wrapper-opus"))
                )
            except TimeoutException:
                 print("Timed out waiting for new content to appear.")

            page_num += 1

        except NoSuchElementException:
            print("No 'Next' button found. Assuming single page of results.")
            break
        except Exception as e:
            print(f"Error clicking next button: {e}")
            break

    return all_works


if __name__ == '__main__':
    # --- IMPORTANT ---
    # You must install selenium and webdriver-manager first:
    # pip install selenium webdriver-manager

    print("Setting up Selenium WebDriver...")
    # This automatically downloads and manages chromedriver
    service = ChromeService(ChromeDriverManager().install())

    # Use headless mode to run without opening a visible browser window
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=service, options=options)

    print("WebDriver set up successfully.")

    try:
        names = get_all_author_names()

        if not names:
            print("No authors found. Exiting.")
            driver.quit()
            exit()

        # todo modify here after testing
        # --- For testing, just run on the first 3 authors ---
        # test_names = ['Ady Endre', 'Apollinaire, Guillaume']
        # print(f"Testing with first 3 authors: {test_names}")

        # --- To run on all authors, comment out the line above and uncomment the line below ---
        test_names = names

        all_author_works = {}

        for name in test_names:
            print(f"\n--- Getting all works for: {name} ---")
            works = get_all_works_for_author(driver, name)
            # Remove duplicates if any, preserving order
            seen = set()
            unique_works = []
            for w in works:
                if w not in seen:
                    unique_works.append(w)
                    seen.add(w)
            
            all_author_works[name] = unique_works
            # note: raw might be way higher because poets tend to have a cumulative edit with all their works uploaded
            print(f"*** Total works found for {name}: {len(unique_works)} (Raw: {len(works)}) ***")

        print("\nScraping complete, writing results to files...")
        # Use absolute path relative to script location to avoid CWD issues
        script_dir = Path(__file__).parent.resolve()
        output_dir = script_dir.parent / 'dia_downloads' / '_summary.json'
        
        # Ensure directory exists
        output_dir.parent.mkdir(parents=True, exist_ok=True)

        with open(output_dir, 'w', encoding='utf-8') as f:
            json.dump(all_author_works, f, ensure_ascii=False, indent=2)
        print(f"Results written to {output_dir}")

    finally:
        # Ensure the browser is closed even if an error occurs
        print("Closing browser.")
        driver.quit()
