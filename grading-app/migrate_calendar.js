import { neon } from '@neondatabase/serverless';
import dotenv from 'dotenv';

dotenv.config();

if (!process.env.DATABASE_URL) {
    console.error("DATABASE_URL is not set.");
    process.exit(1);
}

const sql = neon(process.env.DATABASE_URL);

async function migrateCalendar() {
    try {
        await sql`
            CREATE TABLE IF NOT EXISTS calendar_entries (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                link TEXT,
                snippet TEXT,
                is_literature BOOLEAN DEFAULT TRUE,
                valid_dates TEXT[],
                categories TEXT[],
                ai_rating INTEGER,
                ai_reason TEXT,
                ai_checked BOOLEAN DEFAULT FALSE
            )
        `;

        await sql`
            CREATE TABLE IF NOT EXISTS calendar_votes (
                id SERIAL PRIMARY KEY,
                entry_id INTEGER REFERENCES calendar_entries(id),
                rating INTEGER CHECK (rating >= 0 AND rating <= 5),
                date_class VARCHAR(20),
                corrected_date TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        `;

        await sql`CREATE INDEX IF NOT EXISTS idx_calendar_entries_ai_checked ON calendar_entries(ai_checked)`;
        await sql`CREATE INDEX IF NOT EXISTS idx_calendar_votes_entry_id ON calendar_votes(entry_id)`;

        console.log("Calendar migration successful.");
    } catch (e) {
        console.error("Calendar migration failed:", e);
    }
}

migrateCalendar();
