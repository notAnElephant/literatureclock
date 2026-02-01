import { neon } from '@neondatabase/serverless';
import { config } from 'dotenv';
import fs from 'fs';
import path from 'path';

// Load environment variables
config();

const DATABASE_URL = process.env.DATABASE_URL;
const sql = neon(DATABASE_URL);

async function seedDatabase() {
  try {
    console.log('Starting database seeding...');

    // Read the JSONL file
    const filePath = path.join(process.cwd(), '..', 'scrapers', 'mek_search', 'mek_search_results.jsonl');
    const fileContent = fs.readFileSync(filePath, 'utf-8');
    const lines = fileContent.trim().split('\n');

    console.log(`Found ${lines.length} lines in the file`);

    let processedCount = 0;
    let insertedCount = 0;

    for (const line of lines) {
      if (!line.trim()) continue;

      try {
        const entry = JSON.parse(line);
        processedCount++;

        // Skip entries that are just counts (no actual content)
        if (entry.count !== undefined) {
          continue;
        }

        // Only process literature entries
        if (!entry.is_literature) {
          continue;
        }

        // Skip entries that don't have the required fields
        if (!entry.title || !entry.snippet) {
          continue;
        }

        // Insert into database with the correct columns
        await sql`
          INSERT INTO entries (title, link, snippet, is_literature, valid_times)
          VALUES (${entry.title}, ${entry.link || ''}, ${entry.snippet}, ${entry.is_literature}, ${JSON.stringify(entry.valid_times || [])})
        `;

        insertedCount++;

        if (insertedCount % 100 === 0) {
          console.log(`Inserted ${insertedCount} entries...`);
        }

      } catch (parseError) {
        console.error('Error parsing line:', parseError.message);
        continue;
      }
    }

    console.log(`Seeding complete! Processed ${processedCount} lines, inserted ${insertedCount} entries.`);

  } catch (error) {
    console.error('Database seeding error:', error.message);
  }
}

seedDatabase();