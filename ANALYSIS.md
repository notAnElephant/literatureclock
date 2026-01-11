# Literature Clock - Hungarian Edition

## Project Overview
This project is designed to create a "Literature Clock" using quotes from Hungarian literary works. It automates the process of scraping digital libraries, extracting time references from texts, and compiling them into a dataset.

## Core Components

### 1. Data Collection (Scrapers)
The project sources texts from two major Hungarian digital libraries:
*   **MEK (Magyar Elektronikus Könyvtár)**:
    *   **Script**: `scrapers/mek_scraper.py`
    *   **Method**: Uses `requests` and `BeautifulSoup`.
    *   **Features**: Respects `robots.txt`, handles multiple file formats (HTML, RTF, PDF), and prioritizes HTML. It searches for a predefined list of authors (e.g., Jókai Mór, Kosztolányi Dezső).
    *   **Output**: Downloads files to `mek_downloads/<Author Name>/`.
*   **DIA (Digitális Irodalmi Akadémia)**:
    *   **Script**: `scrapers/dia_scraper.py`
    *   **Method**: Uses `Selenium` (headless Chrome) to navigate the dynamic UI.
    *   **Features**: Iterates through author pages and pagination to find work URLs.
    *   **Status**: Appears to be in a testing/experimental phase compared to the MEK scraper.

### 2. Time Extraction
*   **Script**: `extractor.py`
*   **Configuration**: `rules.json5`
*   **Logic**:
    *   Reads text/HTML files.
    *   Normalizes text (handling Hungarian accents).
    *   Applies regex patterns defined in `rules.json5` to find time expressions (e.g., "10:15", "tíz óra", "háromnegyed öt").
    *   **Disambiguation**: Uses context (words like "reggel", "este") to resolve 12-hour format ambiguities (e.g., 2 o'clock vs 14:00).
*   **Output**: JSON Lines format containing the match, normalized time, and context.

### 3. Analysis & Stats
*   **Script**: `stats.py`
*   **Function**: Analyzes the extraction results (`hits.jsonl`) to show coverage (which minutes of the day have quotes) and rule usage distribution.

## Directory Structure
*   `scrapers/`: Contains the scraping logic.
*   `dia_downloads/` & `mek_downloads/`: Storage for downloaded literary works.
*   `rules.json5`: Regex rules and word-to-number mappings for Hungarian time expressions.
*   `extractor.py`: Main extraction executable.

## Current State & Notes
*   **MEK Scraper**: Well-structured, handles errors and rate limiting.
*   **DIA Scraper**: Uses Selenium, currently set to test with a few authors.
*   **Extraction**: "Strict" mode is enabled in rules, meaning it prioritizes exact minute matches.
*   **Known Issues**: Some MEK novels are only linked as chapter HTMLs, requiring better crawler logic to merge them (noted in `readme.md`).
