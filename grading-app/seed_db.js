import { neon } from '@neondatabase/serverless';
import fs from 'fs';
import readline from 'readline';
import dotenv from 'dotenv';

dotenv.config();

const DATABASE_URL = process.env.DATABASE_URL;
const INPUT_FILE = '../scrapers/mek_search/mek_search_results.jsonl';

if (!DATABASE_URL) {
  console.error("DATABASE_URL not found in .env");
  process.exit(1);
}

const sql = neon(DATABASE_URL);

async function seed() {
  console.log("Starting seeding process...");

  // Create tables
  await sql`DROP TABLE IF EXISTS votes CASCADE`;
  await sql`DROP TABLE IF EXISTS entries CASCADE`;
  await sql`
    CREATE TABLE entries (
      id SERIAL PRIMARY KEY,
      title TEXT NOT NULL,
      link TEXT,
      snippet TEXT,
      is_literature BOOLEAN,
      valid_times TEXT[],
      categories TEXT[]
    )
  `;
  await sql`
    CREATE TABLE votes (
      id SERIAL PRIMARY KEY,
      entry_id INTEGER REFERENCES entries(id),
      rating INTEGER CHECK (rating >= 1 AND rating <= 5),
      am_pm VARCHAR(20),
      created_at TIMESTAMP DEFAULT NOW()
    )
  `;

  const fileStream = fs.createReadStream(INPUT_FILE);
  const rl = readline.createInterface({
    input: fileStream,
    crlfDelay: Infinity
  });

  let count = 0;
  let batch = [];
  const BATCH_SIZE = 100; // Smaller batches for HTTP driver stability

  for await (const line of rl) {
    if (!line.trim()) continue;
    try {
      const data = JSON.parse(line);
      batch.push({
        title: data.title || '',
        link: data.link || '',
        snippet: data.snippet || '',
        is_literature: !!data.is_literature,
        valid_times: data.valid_times || [],
        categories: data.topics || []
      });

      if (batch.length >= BATCH_SIZE) {
        await insertBatch(batch);
        count += batch.length;
        process.stdout.write(`\rInserted ${count} entries...`);
        batch = [];
      }
    } catch (e) {
      console.error("\nError parsing line:", e.message);
    }
  }

  if (batch.length > 0) {
    await insertBatch(batch);
    count += batch.length;
    console.log(`\rInserted ${count} entries.`);
  }

  console.log("\nSeeding completed successfully.");
}

async function insertBatch(batch) {
  // Construct a single multi-row insert query
  // Example: INSERT INTO entries (title, link, snippet, is_literature, valid_times, categories) VALUES ($1, ...), ...
  const values = [];
  const placeholders = [];
  
  batch.forEach((item, i) => {
    const offset = i * 6;
    placeholders.push(`($${offset + 1}, $${offset + 2}, $${offset + 3}, $${offset + 4}, $${offset + 5}, $${offset + 6})`);
    values.push(item.title, item.link, item.snippet, item.is_literature, item.valid_times, item.categories);
  });

  const query = `
    INSERT INTO entries (title, link, snippet, is_literature, valid_times, categories) 
    VALUES ${placeholders.join(', ')}
  `;

  await sql(query, values);
}

seed().catch(err => {
  console.error("\nSeeding failed:", err);
  process.exit(1);
});
