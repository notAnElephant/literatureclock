import json
import os
import psycopg2
from psycopg2.extras import execute_values

INPUT_FILE = 'scrapers/mek_search/mek_search_results.jsonl'
DATABASE_URL = 'YOUR_CONNECTION_STRING'

def seed():
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable not set.")
        return

    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    print("Connecting to Neon...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("Creating tables...")
    cur.execute("""
        DROP TABLE IF EXISTS votes;
        DROP TABLE IF EXISTS entries;

        CREATE TABLE entries (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            link TEXT,
            snippet TEXT,
            is_literature BOOLEAN,
            valid_times TEXT[],
            categories TEXT[]
        );

        CREATE TABLE votes (
            id SERIAL PRIMARY KEY,
            entry_id INTEGER REFERENCES entries(id),
            rating INTEGER CHECK (rating >= 0 AND rating <= 5),
            am_pm VARCHAR(20),
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    print("Reading entries and batch inserting...")
    batch_size = 1000
    batch = []
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                batch.append((
                    data.get('title', ''),
                    data.get('link', ''),
                    data.get('snippet', ''),
                    data.get('is_literature', False),
                    data.get('valid_times', []),
                    data.get('topics', [])
                ))

                if len(batch) >= batch_size:
                    insert_batch(cur, batch)
                    batch = []
                    print(f"Inserted {batch_size} entries...")
            except Exception as e:
                print(f"Skip error: {e}")

        if batch:
            insert_batch(cur, batch)
            print(f"Inserted final {len(batch)} entries.")

    conn.commit()
    cur.close()
    conn.close()
    print("\nSeeding completed! ")

def insert_batch(cur, batch):
    query = "INSERT INTO entries (title, link, snippet, is_literature, valid_times, categories) VALUES %s"
    execute_values(cur, query, batch)

if __name__ == '__main__':
    seed()
