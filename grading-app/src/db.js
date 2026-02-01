// Database connection setup
const { Client } = require('pg');

const client = new Client({
    connectionString: process.env.DATABASE_URL || 'postgresql://neondb_owner:npg_Tm2NVvRF8dgq@ep-floral-lake-ag2btm13-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require',
});

client.connect()
    .then(() => console.log('Connected to the Neon database'))
    .catch(err => console.error('Connection error', err.stack))
    .finally(() => client.end());
