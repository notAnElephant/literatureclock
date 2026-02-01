import { neon } from '@neondatabase/serverless';
import { DATABASE_URL } from '$env/static/private';

// Fallback to process.env for development
const dbUrl = DATABASE_URL || process.env.DATABASE_URL;

if (!dbUrl) {
  throw new Error('DATABASE_URL is not set');
}

export const sql = neon(dbUrl);
