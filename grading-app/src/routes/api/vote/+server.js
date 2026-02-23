import { sql } from '$lib/server/db';
import { json } from '@sveltejs/kit';

export async function POST({ request }) {
    try {
        const { entry_id, rating, am_pm, corrected_time, dataset, class_value, corrected_value } = await request.json();
        const mode = dataset === 'date' ? 'date' : 'time';
        const finalClass = class_value || am_pm;
        const finalCorrected = corrected_value !== undefined ? corrected_value : corrected_time;

        if (mode === 'date') {
            await sql`
                INSERT INTO calendar_votes (entry_id, rating, date_class, corrected_date)
                VALUES (${entry_id}, ${rating}, ${finalClass}, ${finalCorrected || null})
            `;
        } else {
            await sql`
                INSERT INTO votes (entry_id, rating, am_pm, corrected_time)
                VALUES (${entry_id}, ${rating}, ${finalClass}, ${finalCorrected || null})
            `;
        }
        
        return json({ success: true });
    } catch (e) {
        console.error("Vote Error:", e);
        return json({ error: "Failed to save vote" }, { status: 500 });
    }
}
