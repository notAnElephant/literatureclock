import { sql } from '$lib/server/db';
import { json } from '@sveltejs/kit';

export async function GET() {
    try {
        const result = await sql`
            SELECT 
                (SELECT COUNT(*) FROM entries e 
                 WHERE is_literature = true 
                 AND ai_checked = true 
                 AND NOT EXISTS (SELECT 1 FROM votes v WHERE v.entry_id = e.id AND v.corrected_time = 'AI_DENY')
                ) as total_entries,
                (SELECT COUNT(*) FROM entries e 
                 WHERE is_literature = true 
                 AND ai_checked = true 
                 AND EXISTS (SELECT 1 FROM votes v WHERE v.entry_id = e.id AND v.rating > 0 AND v.corrected_time IS NULL)
                 AND NOT EXISTS (SELECT 1 FROM votes v2 WHERE v2.entry_id = e.id AND v2.corrected_time = 'AI_DENY')
                ) as voted_entries,
                (SELECT AVG(v.rating) 
                 FROM votes v 
                 JOIN entries e ON v.entry_id = e.id 
                 WHERE v.rating > 0 
                 AND e.is_literature = true
                 AND v.corrected_time IS NULL
                 AND NOT EXISTS (SELECT 1 FROM votes v2 WHERE v2.entry_id = e.id AND v2.corrected_time = 'AI_DENY')
                ) as average_rating
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