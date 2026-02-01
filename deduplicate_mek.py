import json
import hashlib
import os

INPUT_FILE = 'scrapers/mek_search/mek_search_results.jsonl'
OUTPUT_FILE = 'scrapers/mek_search/mek_search_results_unique.jsonl'

def deduplicate():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    seen_hashes = set()
    removed_count = 0
    total_count = 0
    
    print(f"Deduplicating {INPUT_FILE}...")
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as infile, \
         open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            stripped_line = line.strip()
            if not stripped_line:
                continue
            
            total_count += 1
            # Using a hash to save memory
            line_hash = hashlib.md5(stripped_line.encode('utf-8')).hexdigest()
            
            if line_hash not in seen_hashes:
                seen_hashes.add(line_hash)
                outfile.write(line + '\n')
            else:
                removed_count += 1

    print(f"\nProcessing complete:")
    print(f"Total lines processed: {total_count}")
    print(f"Duplicate lines removed: {removed_count}")
    print(f"Unique lines remaining: {total_count - removed_count}")
    
    # Replace original file with the deduplicated one
    os.replace(OUTPUT_FILE, INPUT_FILE)
    print(f"\nSuccessfully updated {INPUT_FILE}")

if __name__ == '__main__':
    deduplicate()
