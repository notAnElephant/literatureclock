import { sql } from '$lib/server/db';
import { json } from '@sveltejs/kit';

export async function GET() {
    try {
        const result = await sql`
            SELECT 
                (SELECT COUNT(*) FROM entries WHERE is_literature = true) as total_entries,
                (SELECT COUNT(DISTINCT v.entry_id) 
                 FROM votes v 
                 JOIN entries e ON v.entry_id = e.id 
                 WHERE e.is_literature = true) as voted_entries,
                (SELECT AVG(v.rating) 
                 FROM votes v 
                 JOIN entries e ON v.entry_id = e.id 
                 WHERE v.rating > 0 AND e.is_literature = true) as average_rating
        `;
        
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