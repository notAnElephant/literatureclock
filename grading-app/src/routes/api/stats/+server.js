import { sql } from '$lib/server/db';
import { json } from '@sveltejs/kit';

export async function GET({ url }) {
    try {
        const dataset = url.searchParams.get('dataset') === 'date' ? 'date' : 'time';
        const result = dataset === 'date'
            ? await sql`
                SELECT 
                    (SELECT COUNT(*) FROM calendar_entries e 
                     WHERE is_literature = true 
                     AND NOT EXISTS (SELECT 1 FROM calendar_votes v WHERE v.entry_id = e.id AND v.corrected_date = 'AI_DENY')
                    ) as total_entries,
                    (SELECT COUNT(*) FROM calendar_entries e 
                     WHERE is_literature = true 
                     AND EXISTS (SELECT 1 FROM calendar_votes v WHERE v.entry_id = e.id AND v.rating > 0 AND v.corrected_date IS NULL)
                     AND NOT EXISTS (SELECT 1 FROM calendar_votes v2 WHERE v2.entry_id = e.id AND v2.corrected_date = 'AI_DENY')
                    ) as voted_entries,
                    (SELECT AVG(v.rating) 
                     FROM calendar_votes v 
                     JOIN calendar_entries e ON v.entry_id = e.id 
                     WHERE v.rating > 0 
                     AND e.is_literature = true
                     AND v.corrected_date IS NULL
                     AND NOT EXISTS (SELECT 1 FROM calendar_votes v2 WHERE v2.entry_id = e.id AND v2.corrected_date = 'AI_DENY')
                    ) as average_rating
            `
            : await sql`
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
        return json({ error: String(e) }, { status: 500 });
    }
}
