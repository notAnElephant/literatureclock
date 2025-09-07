from __future__ import annotations

# --- put near the top ---
import functools
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

PROFILE = os.getenv("MEK_PROFILE", "1") == "1"
SLOW_MS = int(os.getenv("MEK_SLOW_MS", "800"))  # log ops slower than this


def timeit(label):
    def deco(fn):
        if not PROFILE:
            return fn

        @functools.wraps(fn)
        def wrapped(*args, **kwargs):
            t0 = time.monotonic()
            try:
                return fn(*args, **kwargs)
            finally:
                dt = (time.monotonic() - t0) * 1000
                if dt >= SLOW_MS:
                    print(f"[SLOW] {label} took {dt:.0f} ms")

        return wrapped

    return deco


# ---------------- Config ----------------

OUT_DIR = Path('mek_downloads')
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Keep this modest; you can raise to 6–8 if needed
MAX_WORKERS = 4
REQUEST_DELAY_SEC = 0.7  # extra politeness between requests

USER_AGENT = (
    'LiteratureClockHU/1.0 (+mailto:your-email@example.com) '
    'Polite research; respects robots.txt; throttled'
)

# Authors to fetch
AUTHORS = [
    "Jókai Mór",
    "Mikszáth Kálmán",
    "Móricz Zsigmond",
    "Karinthy Frigyes",
    "Kosztolányi Dezső",
    "Krúdy Gyula",
    "Szabó Magda",
    "Ottlik Géza",
    "Déry Tibor",
    "Németh László",
    "Kertész Imre",
    "Esterházy Péter",
    "Mándy Iván",
    "Csáth Géza",
    "Lengyel Péter",
    "Spiró György",
    "Háy János",
    "Grecsó Krisztián",
    "Závada Pál",
    "Dragomán György",
]

# Search endpoints to try (MEK sometimes tweaks paths).
# The scraper will try these in order until one returns results.
SEARCH_ENDPOINTS: Tuple[dict, ...] = (
    # 1) A simple-search style POST (field names may change; adjust if needed)
    {
        'method': 'POST',
        'url': 'https://mek.oszk.hu/hu/search/elfull/',
        'data_builder': lambda author: {
            'dc_title': author,
            # 'dc_': '',
            # 'dc_topic': '',
            # 'id': '',
            'perpage': '100',
        },
    },
)

# MEK item page pattern (stable across the site):
ITEM_URL_RE = re.compile(r'^https?://mek\.oszk\.hu/\d{2,5}/\d{2,6}/?$', re.IGNORECASE)

# We prefer html, then rtf, then pdf
EXT_PRIORITY = ('.html', '.htm', '.rtf')

# ---------------- HTTP helpers ----------------

session = requests.Session()
session.headers.update({'User-Agent': USER_AGENT})


# remove this line (it's ignored):
# session.timeout = 25

# add explicit timeouts in your helpers:
def fetch_text(url: str, method: str = 'GET', **kwargs) -> Optional[str]:
    time.sleep(REQUEST_DELAY_SEC)
    try:
        kwargs.setdefault("timeout", (10, 60))  # connect, read
        resp = session.request(method, url, **kwargs)
        if 200 <= resp.status_code < 400:
            resp.encoding = resp.apparent_encoding or 'utf-8'
            return resp.text
        return None
    except requests.RequestException:
        return None


def fetch_binary(url: str) -> Optional[bytes]:
    time.sleep(REQUEST_DELAY_SEC)
    try:
        resp = session.get(url, stream=True, timeout=(10, 120))
        if 200 <= resp.status_code < 400:
            return resp.content
        return None
    except requests.RequestException:
        return None


# ---------------- robots.txt ----------------

@dataclass(frozen=True)
class RobotsRules:
    disallow: Tuple[str, ...]


def fetch_robots() -> RobotsRules:
    url = 'https://mek.oszk.hu/robots.txt'
    text = fetch_text(url)
    disallow: List[str] = []
    if text:
        # MEK historically had many "Disallow: /path" tokens in a single line.
        for m in re.finditer(r'Disallow:\s*(/[^\s#]+)', text, re.IGNORECASE):
            disallow.append(m.group(1).strip())
    return RobotsRules(tuple(disallow))


def is_allowed_by_robots(url: str, rules: RobotsRules) -> bool:
    try:
        p = urlparse(url)
        path = p.path or '/'
        # if any disallowed prefix matches the beginning of the path -> disallow
        for prefix in rules.disallow:
            if path.startswith(prefix):
                return False
        return True
    except Exception:
        return False


# ---------------- parsing ----------------

def absolutise(base_url: str, href: str) -> str:
    try:
        return urljoin(base_url, href)
    except Exception:
        return href


def ensure_trailing_slash(u: str) -> str:
    # MEK item pages often exist at both .../07324 and .../07324/
    return u if u.endswith('/') else (u + '/')


# 2) Extract from the anchor’s href, not the inner text
def find_item_urls(html: str, base_url: str) -> List[Tuple[str, Optional[str]]]:
    soup = BeautifulSoup(html, 'html.parser')
    items: List[Tuple[str, Optional[str]]] = []

    # Only anchors with class=itemlink
    for a in soup.select('a.itemlink[href]'):
        href = a.get('href', '').strip()
        if not href:
            continue
        abs_url = absolutise(base_url, href)
        # Keep only MEK item-page roots; normalize trailing slash
        if ITEM_URL_RE.match(abs_url):
            url = ensure_trailing_slash(abs_url)
            # Extract dctitle text if present
            dctitle_div = a.find('div', class_='dctitle')
            title = dctitle_div.get_text(strip=True) if dctitle_div else None
            print(f"[find_item_urls] Found href: {href}, title: {title}")
            items.append((url, title))

    # de-dup, keep order
    seen = set()
    uniq = []
    for u, t in items:
        if u not in seen:
            uniq.append((u, t))
            seen.add(u)
    return uniq


def extract_download_links(item_html: str, item_url: str) -> List[str]:
    """Return candidate downloadable file URLs from an item page, prioritised by extension."""
    soup = BeautifulSoup(item_html, 'html.parser')
    links: List[str] = []
    for a in soup.select('a[href]'):
        href = a.get('href', '')
        abs_url = absolutise(item_url, href)
        if not abs_url.lower().startswith('https://mek.oszk.hu/'):
            continue
        lower = abs_url.lower()
        if lower.endswith(EXT_PRIORITY):
            links.append(abs_url)

    # prioritise by extension order defined in EXT_PRIORITY
    def sort_key(u: str) -> Tuple[int, str]:
        lower = u.lower()
        for idx, ext in enumerate(EXT_PRIORITY):
            if lower.endswith(ext):
                return idx, lower
        return len(EXT_PRIORITY), lower

    links.sort(key=sort_key)

    # de-dup while preserving priority
    seen = set()
    ordered = []
    for u in links:
        if u not in seen:
            ordered.append(u)
            seen.add(u)
    return ordered


# ---------------- search ----------------

def search_author(author: str) -> List[Tuple[str, Optional[str]]]:
    """Try multiple endpoints to find item pages for an author."""
    print(f"[search_author] Searching for author: {author}")
    for idx, endpoint in enumerate(SEARCH_ENDPOINTS):
        method = endpoint.get('method', 'GET').upper()
        url = endpoint['url']
        print(f"[search_author] Trying endpoint {idx + 1}: {url} (method: {method})")
        kwargs = {}

        if method == 'POST' and 'data_builder' in endpoint:
            kwargs['data'] = endpoint['data_builder'](author)
            print(f"[search_author] Using POST data: {kwargs['data']}")
        elif method == 'GET' and 'params_builder' in endpoint:
            kwargs['params'] = endpoint['params_builder'](author)
            print(f"[search_author] Using GET params: {kwargs['params']}")

        html = fetch_text(url, method=method, **kwargs)
        if not html:
            print(f"[search_author] No HTML returned from {url}")
            continue

        items = find_item_urls(html, url)
        print(f"[search_author] Found {len(items)} item URLs at {url}")
        if items:
            return items

    print(f"[search_author] No items found for author: {author}")
    return []


# ---------------- download orchestration ----------------

def safe_filename(s: str, max_len: int = 160) -> str:
    s = re.sub(r'[\\/:*?"<>|]+', '_', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s[:max_len] if len(s) > max_len else s


def guess_title_from_item(item_url: str) -> str:
    # Fallback: use the last path segment if no better title
    try:
        return safe_filename(Path(urlparse(item_url).path).name or 'untitled')
    except Exception:
        return 'untitled'


def _get_main_content_link(item_html: str, item_url: str) -> Optional[str]:
    soup = BeautifulSoup(item_html, "html.parser")
    # Extract the numeric item id from the URL path (e.g., ".../07324/").
    try:
        parts = [p for p in Path(urlparse(item_url).path).parts if p]
        item_id = parts[-1]  # "07324"
    except Exception:
        return None

    # Collect anchors that point to "<item_id>.<ext>" where ext in EXT_PRIORITY
    candidates: List[Tuple[int, str]] = []
    for a in soup.select('a[href]'):
        href = a.get("href", "").strip()
        if not href:
            continue
        abs_url = absolutise(item_url, href)
        lower = abs_url.lower()
        for idx, ext in enumerate(EXT_PRIORITY):
            if lower.endswith(f"/{item_id}{ext}") or lower.endswith(f"{item_id}{ext}"):
                candidates.append((idx, abs_url))
                break

    if not candidates:
        return None

    # Choose by extension priority (HTML/HTM > RTF > PDF)
    candidates.sort(key=lambda t: (t[0], t[1].lower()))
    return candidates[0][1]


def _first_p_text(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")
    p = soup.find("p")
    if not p:
        return None
    txt = p.get_text(separator=" ", strip=True)
    return txt or None


def download_best_formats(item_url: str, title: Optional[str], author_dir: Path, robots: RobotsRules) -> dict:
    """Download only the main content file (<id>.<ext>) and name it from the dctitle if available, else from the first <p> text."""
    page_html = fetch_text(item_url)
    if not page_html:
        return {"item": item_url, "status": "item_page_failed"}

    main_url = _get_main_content_link(page_html, item_url)
    if not main_url:
        return {"item": item_url, "status": "main_content_not_found"}

    if not is_allowed_by_robots(main_url, robots):
        return {"item": item_url, "status": "disallowed_by_robots", "url": main_url}

    # Determine filename prefix: prefer dctitle, else first <p>, else fallback
    name_prefix: Optional[str] = None
    main_ext = Path(urlparse(main_url).path).suffix.lower()

    if title:
        name_prefix = title
        print(f"[download_best_formats] Using dctitle for filename: {title}")
    elif main_ext in (".html", ".htm"):
        main_html = fetch_text(main_url)
        if main_html:
            name_prefix = _first_p_text(main_html)
            print(f"[download_best_formats] Using <p> text for filename: {name_prefix}")
    else:
        # Try to locate a sibling HTML variant for naming: .../<id>.html or .htm
        try:
            parts = [p for p in Path(urlparse(item_url).path).parts if p]
            item_id = parts[-1]
            base_dir = item_url if item_url.endswith("/") else item_url + "/"
            for ext in (".html", ".htm"):
                html_variant = absolutise(base_dir, f"{item_id}{ext}")
                if is_allowed_by_robots(html_variant, robots):
                    html_text = fetch_text(html_variant)
                    if html_text:
                        name_prefix = _first_p_text(html_text)
                        if name_prefix:
                            print(f"[download_best_formats] Using sibling HTML <p> text for filename: {name_prefix}")
                            break
        except Exception:
            pass

    # Finalise filename
    if not name_prefix:
        name_prefix = guess_title_from_item(item_url)  # fallback
        print(f"[download_best_formats] Using fallback for filename: {name_prefix}")
    fname = safe_filename(name_prefix) + main_ext
    out_path = author_dir / fname

    if out_path.exists():
        return {"item": item_url, "status": "ok", "files": [str(out_path)], "url": main_url}

    content = fetch_binary(main_url)
    if not content:
        return {"item": item_url, "status": "download_failed", "url": main_url}

    out_path.write_bytes(content)
    return {"item": item_url, "status": "ok", "files": [str(out_path)], "url": main_url}


def process_author(author: str, robots: RobotsRules) -> dict:
    print(f'\n=== Author: {author} ===')
    items = search_author(author)
    print(f'Found {len(items)} candidate item pages.')

    author_dir = OUT_DIR / safe_filename(author)
    author_dir.mkdir(parents=True, exist_ok=True)

    reports = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(download_best_formats, u, t, author_dir, robots) for u, t in items]
        for fut in as_completed(futures):
            reports.append(fut.result())

    ok = sum(1 for r in reports if r.get('status') == 'ok')
    print(f'Done: {ok}/{len(items)} items saved (see "{author_dir}").')
    return {'author': author, 'items': len(items), 'saved': ok, 'reports': reports}


def main() -> None:
    robots = fetch_robots()
    if robots.disallow:
        print('Robots.txt disallow prefixes:', robots.disallow[:8], '...')

    all_reports = []
    for author in AUTHORS:
        rep = process_author(author, robots)
        all_reports.append(rep)

    # Write a small JSON summary
    (OUT_DIR / '_summary.json').write_text(
        json.dumps(all_reports, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print('\nAll done. Summary saved to', OUT_DIR / '_summary.json')


if __name__ == '__main__':
    main()
