import json
import re
import time
import argparse
import random
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_rules(path):
    """Loads rules.json5, stripping comments."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        content = re.sub(r'//.*', '', content)
        return json.loads(content)
    except Exception as e:
        logging.error(f"Failed to load rules from {path}: {e}")
        return None

class TimeTermGenerator:
    def __init__(self, rules):
        self.rules = rules
        self.number_words = rules.get('number_words', {})
        
    def get_number_word(self, n):
        n_str = str(n)
        words = []
        if n_str in self.number_words:
            return self.number_words[n_str]
        if 13 <= n <= 19:
            prefix = self.number_words.get('13_19_prefix', ['tizen'])[0]
            digit = n % 10
            digit_words = self.get_number_word(digit)
            for dw in digit_words:
                words.append(prefix + dw)
        elif 21 <= n <= 29:
            prefix = self.number_words.get('20s_prefix', ['huszon'])[0]
            digit = n % 10
            digit_words = self.get_number_word(digit)
            for dw in digit_words:
                words.append(prefix + dw)
        elif n == 20:
             return self.number_words.get('20_exact', ['húsz'])
        elif n == 30:
             return self.number_words.get('30_exact', ['harminc'])
        elif 31 <= n <= 39:
            prefix = self.number_words.get('30s_prefix', ['harminc'])[0]
            digit = n % 10
            digit_words = self.get_number_word(digit)
            for dw in digit_words:
                words.append(prefix + dw)
        elif n == 40:
             return self.number_words.get('40_exact', ['negyven'])
        elif 41 <= n <= 49:
            prefix = self.number_words.get('40s_prefix', ['negyven'])[0]
            digit = n % 10
            digit_words = self.get_number_word(digit)
            for dw in digit_words:
                words.append(prefix + dw)
        elif n == 50:
             return self.number_words.get('50_exact', ['ötven'])
        elif 51 <= n <= 59:
            prefix = self.number_words.get('50s_prefix', ['ötven'])[0]
            digit = n % 10
            digit_words = self.get_number_word(digit)
            for dw in digit_words:
                words.append(prefix + dw)
        if not words and n_str in self.number_words:
             return self.number_words[n_str]
        return words if words else [str(n)]

    def generate_terms(self, h, m):
        terms = set()
        terms.add(f"{h}:{m:02}")
        terms.add(f"{h:02}:{m:02}")
        terms.add(f"{h}.{m:02}")
        terms.add(f"{h:02}.{m:02}")
        terms.add(f"{h} óra {m} perc")
        terms.add(f"{h:02} óra {m:02} perc")
        terms.add(f"{h} óra {m:02} perc")
        
        h_words = self.get_number_word(h)
        m_words = self.get_number_word(m)
        
        for hw in h_words:
            for mw in m_words:
                terms.add(f"{hw} óra {mw} perc")
            terms.add(f"{hw} óra {m} perc")
            terms.add(f"{hw} óra {m:02} perc")

        if m == 0:
            terms.add(f"{h} óra")
            terms.add(f"{h:02} óra")
            terms.add(f"{h} órakor")
            terms.add(f"{h}-kor")
            for hw in h_words:
                terms.add(f"{hw} óra")
                terms.add(f"{hw} órakor")
                terms.add(f"{hw}-kor") 

        next_h = (h + 1) % 24
        next_h_words = self.get_number_word(next_h)
        
        if m == 30:
            terms.add(f"fél {next_h}")
            for w in next_h_words:
                terms.add(f"fél {w}")
        
        if m == 15:
            terms.add(f"negyed {next_h}")
            for w in next_h_words:
                terms.add(f"negyed {w}")

        if m == 45:
            terms.add(f"háromnegyed {next_h}")
            for w in next_h_words:
                terms.add(f"háromnegyed {w}")

        if m > 0:
             terms.add(f"{m} perccel {h} óra után")
             for mw in m_words:
                 terms.add(f"{mw} perccel {h} óra után")
                 for hw in h_words:
                      terms.add(f"{mw} perccel {hw} óra után")
        
        y_before = 60 - m
        if 0 < y_before < 60:
             target_next_h = (h + 1) % 24
             terms.add(f"{y_before} perccel {target_next_h} óra előtt")
             y_before_words = self.get_number_word(y_before)
             target_next_h_words = self.get_number_word(target_next_h)
             for ybw in y_before_words:
                 terms.add(f"{ybw} perccel {target_next_h} óra előtt")
                 for tnhw in target_next_h_words:
                      terms.add(f"{ybw} perccel {tnhw} óra előtt")

        return list(terms)

class MekSearcher:
    def __init__(self, headless=True):
        self.options = webdriver.ChromeOptions()
        if headless:
            self.options.add_argument("--headless")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)
        self.url = "https://mek.oszk.hu/hu/search/elfulltext/#sealist"
        
    def search(self, term):
        results = []
        try:
            logging.info(f"Navigating to {self.url}...")
            self.driver.get(self.url)
            search_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "body"))
            )
            quoted_term = f'"{term}"'
            logging.info(f"Searching for: {quoted_term}")
            search_input.clear()
            search_input.send_keys(quoted_term)
            submit_btn = self.driver.find_element(By.XPATH, "//input[@type='submit']")
            submit_btn.click()
            time.sleep(2)
            result_divs = self.driver.find_elements(By.CSS_SELECTOR, "div.results, div.elful.results")
            logging.info(f"Found {len(result_divs)} result blocks.")
            for div in result_divs:
                text = div.text
                if "Találatok száma" in text:
                    continue
                try:
                    title_link = div.find_element(By.TAG_NAME, "a")
                    title = title_link.text
                    link = title_link.get_attribute("href")
                except:
                    title = "Unknown"
                    link = ""
                snippet = ""
                try:
                    loc_links = div.find_elements(By.PARTIAL_LINK_TEXT, "Találat helye")
                    if loc_links:
                        snippet = div.text
                except:
                    pass

                if title and title != "Unknown":
                    results.append({
                        "search_term": term,
                        "title": title,
                        "link": link,
                        "snippet": snippet
                    })
        except Exception as e:
            logging.error(f"Error during search for '{term}': {e}")
        return results

    def close(self):
        self.driver.quit()

def main():
    parser = argparse.ArgumentParser(description="Search MEK for time patterns.")
    parser.add_argument("--limit", type=int, default=5, help="Max number of terms to search.")
    parser.add_argument("--output", default="mek_search_results.jsonl", help="Output file path.")
    parser.add_argument("--visible", action="store_true", help="Run browser in visible mode.")
    args = parser.parse_args()

    rules_path = Path(__file__).parent.parent / 'rules.json5'
    rules = load_rules(rules_path)
    if not rules:
        logging.error("Could not load rules. Exiting.")
        return

    generator = TimeTermGenerator(rules)
    searcher = MekSearcher(headless=not args.visible)

    try:
        all_terms = set()
        logging.info("Generating search terms...")
        for h in range(24):
            for m in range(60):
                terms = generator.generate_terms(h, m)
                all_terms.update(terms)
        
        sorted_terms = sorted(list(all_terms))
        logging.info(f"Generated {len(sorted_terms)} unique search terms.")
        
        if args.limit > 0:
            logging.info(f"Test mode: selecting {args.limit} random terms.")
            search_queue = random.sample(sorted_terms, min(args.limit, len(sorted_terms)))
        else:
            search_queue = sorted_terms

        logging.info(f"Starting search for {len(search_queue)} terms...")
        
        with open(args.output, 'w', encoding='utf-8') as f:
            for i, term in enumerate(search_queue):
                logging.info(f"[{i+1}/{len(search_queue)}] Searching: {term}")
                results = searcher.search(term)
                if results:
                    logging.info(f"  -> Found {len(results)} matches.")
                    for res in results:
                        f.write(json.dumps(res, ensure_ascii=False) + "\n")
                else:
                    logging.info("  -> No matches.")
                f.flush()

    finally:
        searcher.close()

if __name__ == "__main__":
    main()
