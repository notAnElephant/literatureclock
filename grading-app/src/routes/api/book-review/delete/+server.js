import { sql } from '$lib/server/db';
import { json } from '@sveltejs/kit';

export async function POST({ request }) {
    try {
        const body = await request.json();
        const dataset = body?.dataset === 'date' ? 'date' : 'time';
        const title = typeof body?.title === 'string' ? body.title.trim() : '';

        if (!title) {
            return json({ error: 'Missing title' }, { status: 400 });
        }

        let deletedVotes = 0;
        let deletedEntries = 0;

        if (dataset === 'date') {
            const voteRows = await sql`
                DELETE FROM calendar_votes v
                USING calendar_entries e
                WHERE v.entry_id = e.id
                  AND e.title = ${title}
                RETURNING v.entry_id
            `;
            deletedVotes = voteRows.length;

            const entryRows = await sql`
                DELETE FROM calendar_entries
                WHERE title = ${title}
                RETURNING id
            `;
            deletedEntries = entryRows.length;
        } else {
            const voteRows = await sql`
                DELETE FROM votes v
                USING entries e
                WHERE v.entry_id = e.id
                  AND e.title = ${title}
                RETURNING v.entry_id
            `;
            deletedVotes = voteRows.length;

            const entryRows = await sql`
                DELETE FROM entries
                WHERE title = ${title}
                RETURNING id
            `;
            deletedEntries = entryRows.length;
        }

        return json({
            success: true,
            dataset,
            title,
            deleted_entries: deletedEntries,
            deleted_votes: deletedVotes
        });
    } catch (e) {
        console.error('Book review delete error:', e);
        return json({ error: 'Failed to delete book entries' }, { status: 500 });
    }
}
