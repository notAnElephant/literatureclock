# Literature Clock Grading App

A generic, mobile-first SvelteKit application for grading literature quotes and classifying them as AM/PM.

## Setup

### 1. Database (Neon Postgres)

1.  Create a new project at [neon.tech](https://neon.tech).
2.  Get your **Connection String** (Pooled is recommended for serverless).
3.  Run the SQL commands from `../seed.sql` in the Neon SQL Editor to create the tables (`entries`, `votes`) and populate them with data.

### 2. Environment Variables

1.  Copy the example file:
    ```bash
    cp .env.example .env
    ```
2.  Edit `.env` and set your `DATABASE_URL`:
    ```
    DATABASE_URL=postgres://user:password@ep-host.neon.tech/neondb
    ```

### 3. Development

Install dependencies (if you haven't already):
```bash
npm install
```

Start the server:
```bash
npm run dev
```

### 4. Deployment (Vercel)

This project is configured with `@sveltejs/adapter-auto`, which works seamlessly with Vercel.

1.  Push this code to GitHub/GitLab/Bitbucket.
2.  Import the project in Vercel.
3.  **Crucial:** Add the `DATABASE_URL` to the **Environment Variables** in your Vercel Project Settings.
4.  Deploy!

## Tech Stack

*   **Framework:** SvelteKit
*   **Styling:** Tailwind CSS
*   **Database:** Neon (PostgreSQL) via `@neondatabase/serverless`