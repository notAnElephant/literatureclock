import { sql } from '$lib/server/db';
import { json } from '@sveltejs/kit';

export async function GET({ url }) {
    try {
        const dataset = url.searchParams.get('dataset') === 'date' ? 'date' : 'time';
        const thresholdParam = Number.parseInt(url.searchParams.get('threshold') ?? '50', 10);
        const threshold = Number.isFinite(thresholdParam) ? Math.max(0, thresholdParam) : 50;

        const rows = dataset === 'date'
            ? await sql`
                SELECT title, COUNT(*)::int AS entry_count
                FROM calendar_entries
                WHERE is_literature = true
                  AND title IS NOT NULL
                  AND title <> ''
                GROUP BY title
                HAVING COUNT(*) > ${threshold}
                ORDER BY COUNT(*) DESC, title ASC
            `
            : await sql`
                SELECT title, COUNT(*)::int AS entry_count
                FROM entries
                WHERE is_literature = true
                  AND title IS NOT NULL
                  AND title <> ''
                GROUP BY title
                HAVING COUNT(*) > ${threshold}
                ORDER BY COUNT(*) DESC, title ASC
            `;

        return json({
            dataset,
            threshold,
            books: rows.map((r) => ({
                title: r.title,
                entry_count: Number.parseInt(r.entry_count, 10) || 0
            }))
        });
    } catch (e) {
        console.error('Book review books error:', e);
        return json({ error: 'Failed to load suspect books' }, { status: 500 });
    }
}
