import { sql } from '$lib/server/db';
import { json } from '@sveltejs/kit';

export async function GET() {
    try {
        const result = await sql`
            SELECT 
                (SELECT COUNT(*) FROM entries) as total_entries,
                (SELECT COUNT(DISTINCT entry_id) FROM votes) as voted_entries,
                (SELECT AVG(rating) FROM votes WHERE rating > 0) as average_rating
        `;
        
        // Ensure numbers are returned (Postgres COUNT returns strings sometimes in JS drivers)
        const stats = {
            total_entries: parseInt(result[0].total_entries) || 0,
            voted_entries: parseInt(result[0].voted_entries) || 0,
            average_rating: parseFloat(result[0].average_rating) || 0
        };

        return json(stats);
    } catch (e) {
        console.error("Stats Error:", e);
        return json({ error: e.message }, { status: 500 });
    }
}
