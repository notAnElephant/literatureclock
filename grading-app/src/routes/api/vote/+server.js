import { sql } from '$lib/server/db';
import { json } from '@sveltejs/kit';

export async function POST({ request }) {
    try {
        const { entry_id, rating, am_pm, corrected_time } = await request.json();
        
        await sql`
            INSERT INTO votes (entry_id, rating, am_pm, corrected_time)
            VALUES (${entry_id}, ${rating}, ${am_pm}, ${corrected_time || null})
        `;
        
        return json({ success: true });
    } catch (e) {
        console.error("Vote Error:", e);
        return json({ error: "Failed to save vote" }, { status: 500 });
    }
}
