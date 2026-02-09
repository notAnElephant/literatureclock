import os
import json
import time
import re
import psycopg2
from psycopg2.extras import execute_values
from openai import OpenAI
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
BATCH_SIZE = 20
DATABASE_URL = os.environ.get('DATABASE_URL')

# LM Studio Configuration
LM_STUDIO_BASE_URL = os.environ.get('LM_STUDIO_BASE_URL', "http://localhost:1234/v1")
DEFAULT_MODEL_NAME = os.environ.get('MODEL_NAME', "local-model")

# Global Counters
total_input_tokens = 0
total_output_tokens = 0

if not DATABASE_URL:
    print("Error: DATABASE_URL is not set.")
    exit(1)

# Initialize OpenAI client for LM Studio
client = OpenAI(base_url=LM_STUDIO_BASE_URL, api_key="lm-studio")

# --- Debug: List available models ---
print(f"Connecting to LM Studio at {LM_STUDIO_BASE_URL}...")
MODEL_NAME = DEFAULT_MODEL_NAME
try:
    models = client.models.list()
    if models.data:
        # Use the first loaded model's ID if our default isn't found
        available_ids = [m.id for m in models.data]
        print(f"Available local models: {', '.join(available_ids)}")
        if DEFAULT_MODEL_NAME not in available_ids:
            MODEL_NAME = available_ids[0]
except Exception as e:
    print(f"Warning: Could not list models: {e}")
print(f"Using model: {MODEL_NAME}\n")
# ------------------------------------

PROMPT_TEMPLATE = """
You are a strict data cleaner for a "Literature Clock" project. 
Your goal is to filter out invalid entries found by a scraper.

The scraper looked for time patterns (e.g. "12:30", "negyed három"), but it found many false positives.
The text is in Hungarian.

Criteria for DENYING an entry (marking it as bad):
1. **Not a Time**: The matching text refers to a date (e.g., "11/12" meaning Nov 12th), a quantity, a price, or a chapter number, NOT a time of day.
2. **Meta-text**: The snippet is a Table of Contents, a header, a footnote, or a bibliography, not a narrative sentence.
3. **Comment**: The data is not of the highest quality, it may include comments made on the book, not just the book's core text.
4. **Gibberish**: The snippet is broken, unreadable, or just a list of numbers.

Criteria for KEEPING:
1. It is a valid sentence from a book, or it is a diary's timestamp
2. It refers to a specific time of day.

Input Data (JSON):
{data}

Output Format (JSON):
Return a list of objects. Each object must have:
- "id": (integer) The entry ID from the input.
- "status": "DENY" or "KEEP"
- "rate": (integer) 0-5 rating of quality (i.e., 0 for DENY, 5 for perfect KEEP)
- "reason": (string) Short explanation (e.g., "Date format", "TOC", "Valid quote").
"""

def get_unchecked_entries(cur, limit):
    cur.execute("""
        SELECT id, title, snippet, valid_times 
        FROM entries 
        WHERE ai_checked IS FALSE 
        AND is_literature IS TRUE
        LIMIT %s
    """, (limit,))
    return cur.fetchall()

def mark_as_checked(cur, ids):
    if not ids: return
    query = "UPDATE entries SET ai_checked = TRUE WHERE id IN %s"
    cur.execute(query, (tuple(ids),))

def insert_deny_votes(cur, denials):
    if not denials: return
    # (entry_id, rating, am_pm, corrected_time)
    values = [(d['id'], 0, 'ambiguous', 'AI_DENY') for d in denials]
    execute_values(cur, """
        INSERT INTO votes (entry_id, rating, am_pm, corrected_time)
        VALUES %s
    """, values)

def process_batch(cur, entries):
    global total_input_tokens, total_output_tokens
    # Prepare data
    input_data = []
    for e in entries:
        # e = (id, title, snippet, valid_times)
        
        # Truncate snippet to 800 characters for context safety
        snippet = e[2] or ""
        if len(snippet) > 800:
            snippet = snippet[:800] + "..."

        input_data.append({
            "id": e[0],
            "title": e[1],
            "snippet": snippet,
            "matched_time": e[3]
        })

    prompt = PROMPT_TEMPLATE.format(data=json.dumps(input_data, ensure_ascii=False))

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a strict data cleaner. Respond only with JSON."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Get usage metadata
        input_token_count = response.usage.prompt_tokens
        output_token_count = response.usage.completion_tokens
        total_input_tokens += input_token_count
        total_output_tokens += output_token_count

        content = response.choices[0].message.content
        # Local models sometimes wrap JSON in code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        results_data = json.loads(content)
        # Handle both list and object with list formats
        if isinstance(results_data, dict):
            # Try to find a list within the dict if it's not a list itself
            for key in results_data:
                if isinstance(results_data[key], list):
                    results = results_data[key]
                    break
            else:
                results = [] # Fallback
        else:
            results = results_data

    except Exception as e:
        print(f"  -> LM Studio Error: {e}")
        return False # Signal failure

    denials = [r for r in results if r.get('status') == 'DENY']
    keeps = [r for r in results if r.get('status') == 'KEEP']
    
    all_ids = [e[0] for e in entries]

    print(f"  -> AI Decision: {len(denials)} DENY, {len(keeps)} KEEP")
    print(f"  -> Tokens: Input +{input_token_count}, Output +{output_token_count}")
    print(f"  -> Total Tokens: {total_input_tokens + total_output_tokens}")

    # DB Updates
    insert_deny_votes(cur, denials)
    mark_as_checked(cur, all_ids)
    return True # Signal success

def main():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False # We'll commit after each batch
    cur = conn.cursor()

    total_processed = 0

    try:
        while True:
            entries = get_unchecked_entries(cur, BATCH_SIZE)
            if not entries:
                print("No more unchecked entries found.")
                break

            print(f"Processing batch of {len(entries)} entries...")
            success = process_batch(cur, entries)
            
            if success == "RETRY":
                continue # Try the same batch again
                
            if not success:
                print("Batch processing failed. Stopping script.")
                break
            
            conn.commit()
            
            total_processed += len(entries)
            print(f"Total processed so far: {total_processed}")
            
            # Small delay to keep the local machine responsive
            time.sleep(1.0) 

    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"\nCritical Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    main()
