// Test script to verify database connection
import { sql } from '$lib/server/db.js';

export async function GET() {
  try {
    const result = await sql`SELECT * FROM entries LIMIT 1`;
    return new Response(JSON.stringify({ success: true, data: result[0] }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Database test error:', error);
    return new Response(JSON.stringify({ success: false, error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}