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
        await sql`ALTER TABLE votes ADD COLUMN IF NOT EXISTS corrected_time VARCHAR(10)`;
        console.log("Migration successful: added corrected_time column.");
    } catch (e) {
        console.error("Migration failed:", e);
    }
}
migrate();
