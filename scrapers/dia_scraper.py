from pathlib import Path

from bs4 import BeautifulSoup
import re


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
    dia_scraper()

