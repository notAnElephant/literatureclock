import { sql } from '$lib/server/db';
import { json } from '@sveltejs/kit';

export async function GET() {
    try {
        let entry = null;
        let attempts = 0;
        
        // Find a valid entry, auto-denying bad ones
        while (!entry && attempts < 20) {
            attempts++;
            
            const result = await sql`
                SELECT * FROM entries 
                WHERE id NOT IN (SELECT entry_id FROM votes)
                AND is_literature = true
                ORDER BY RANDOM() 
                LIMIT 1
            `;
            
            const candidate = result[0];
            if (!candidate) break;

            const snippetText = candidate.snippet ? candidate.snippet.toLowerCase() : "";
            const isInvalid = !candidate.snippet || 
                              candidate.snippet.trim() === "" || 
                              snippetText.includes("no snippet is available");

            if (isInvalid) {
                // Auto-deny
                await sql`
                    INSERT INTO votes (entry_id, rating, am_pm)
                    VALUES (${candidate.id}, 0, 'ambiguous')
                `;
                continue;
            }
            
            entry = candidate;
        }

        if (!entry) {
            return json({ error: "No valid entries available" }, { status: 404 });
        }

        return json(entry);
    } catch (e) {
        console.error("DB Error:", e);
        return json({ error: "Database connection failed" }, { status: 500 });
    }
}