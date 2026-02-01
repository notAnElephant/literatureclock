import { sql } from '$lib/server/db';
import { json } from '@sveltejs/kit';

export async function POST({ request }) {
    try {
        const { entry_id, rating, am_pm } = await request.json();
        
        await sql`
            INSERT INTO votes (entry_id, rating, am_pm)
            VALUES (${entry_id}, ${rating}, ${am_pm})
        `;
        
        return json({ success: true });
    } catch (e) {
        console.error("Vote Error:", e);
        return json({ error: "Failed to save vote" }, { status: 500 });
    }
}
