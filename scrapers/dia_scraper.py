from pathlib import Path

import requests
from bs4 import BeautifulSoup
import re


# todo this only gets the links for the authors, not the links to all of their novels/poems
'''
Extracts all author links from the DIA homepage.
'''
def get_all_author_links():
    response = requests.get('https://dia.hu/')
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    author_links = []

    for link in soup.select('a.authors-block--author'):
        href = link.get('href')
        if href:
            full_url = f'https://dia.hu{href}'
            author_links.append(full_url)

    return author_links


# TODO this works for the local file, but lets make it download from the web too
def dia_scraper():
    html = Path('/Users/oraisz/Downloads/solr').read_text(encoding='utf-8')
    soup = BeautifulSoup(html, 'html.parser')

    urls = []

    for record in soup.select('div.data-wrapper-opus'):
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

        url = f'http://reader.dia.hu/online-reader/open?epubId={epub_id}&component={component}&locale=hu'
        urls.append(url)

    print(f'Found {len(urls)} reader URLs:')

    # TODO extract the text using the links
    for u in urls:
        print(u)


if __name__ == '__main__':
    # dia_scraper()
    links = get_all_author_links()
    print(links)

