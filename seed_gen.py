import json
import os

INPUT_FILE = 'scrapers/mek_search/mek_search_results.jsonl'
OUTPUT_SQL = 'seed.sql'

def escape_sql(text):
    if text is None:
        return "NULL"
    return "'" + text.replace("'", "''") + "'"

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    print(f"Generating {OUTPUT_SQL}...")
    
    with open(OUTPUT_SQL, 'w', encoding='utf-8') as sql_file:
        # Create Tables
        sql_file.write("""
DROP TABLE IF EXISTS votes;
DROP TABLE IF EXISTS entries;

CREATE TABLE entries (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    link TEXT,
    snippet TEXT,
    is_literature BOOLEAN,
    valid_times TEXT[]
);

CREATE TABLE votes (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER REFERENCES entries(id),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    am_pm VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert Data
""")
        
        count = 0
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    # Filter for literature if desired, but user said "remove duplicates" 
                    # earlier and kept all unique. Let's keep all unique lines.
                    
                    title = data.get('title', '')
                    link = data.get('link', '')
                    snippet = data.get('snippet', '')
                    is_lit = str(data.get('is_literature', False)).lower()
                    # valid_times is a list, we can store as Postgres array
                    valid_times = data.get('valid_times', [])
                    
                    # Construct Array String: '{ "00:00", "12:00" }'
                    valid_times_str = '{' + ','.join([f'"{t}"' for t in valid_times]) + '}'
                    
                    sql = f"INSERT INTO entries (title, link, snippet, is_literature, valid_times) VALUES ({escape_sql(title)}, {escape_sql(link)}, {escape_sql(snippet)}, {is_lit}, '{valid_times_str}');\n"
                    sql_file.write(sql)
                    count += 1
                except json.JSONDecodeError:
                    continue
        
        print(f"Finished. Generated SQL for {count} entries.")

if __name__ == '__main__':
    main()
