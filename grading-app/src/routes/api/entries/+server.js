import { sql } from '$lib/server/db';
import { json } from '@sveltejs/kit';

export async function GET() {
    // Select a random entry
    // Ideally: SELECT * FROM entries WHERE id NOT IN (SELECT entry_id FROM votes) ORDER BY RANDOM() LIMIT 1
    // But for performance on larger datasets, simple random is fine to start.
    try {
        const result = await sql`
            SELECT * FROM entries 
            ORDER BY RANDOM() 
            LIMIT 1
        `;
        return json(result[0] || null);
    } catch (e) {
        console.error("DB Error:", e);
        return json({ error: "Database connection failed" }, { status: 500 });
    }
}
