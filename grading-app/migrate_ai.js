import { neon } from '@neondatabase/serverless';
import dotenv from 'dotenv';
dotenv.config();

if (!process.env.DATABASE_URL) {
    console.error("DATABASE_URL is not set.");
    process.exit(1);
}

const sql = neon(process.env.DATABASE_URL);

async function migrate() {
    try {
        await sql`ALTER TABLE entries ADD COLUMN IF NOT EXISTS ai_checked BOOLEAN DEFAULT FALSE`;
        await sql`CREATE INDEX IF NOT EXISTS idx_entries_ai_checked ON entries(ai_checked)`;
        console.log("Migration successful: added ai_checked column.");
    } catch (e) {
        console.error("Migration failed:", e);
    }
}
migrate();
