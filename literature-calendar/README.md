# Literature Calendar

This subproject mirrors the Literature Clock pipeline, but for date-like snippets.

## Source Site

- `https://mek.oszk.hu/hu/search/elfulltext/#sealist`

## Files

- Rules: `/Users/oraisz/code/largeprojects/literatureclock/rules_calendar.json5`
- Searcher: `/Users/oraisz/code/largeprojects/literatureclock/scrapers/mek_search/mek_calendar_search.py`
- Seeder: `/Users/oraisz/code/largeprojects/literatureclock/seed_calendar_db.py`
- AI grader: `/Users/oraisz/code/largeprojects/literatureclock/calendar_ai_grader.py`
- App migration: `/Users/oraisz/code/largeprojects/literatureclock/grading-app/migrate_calendar.js`

## Run Order

1. Run search:
   - `python3 /Users/oraisz/code/largeprojects/literatureclock/scrapers/mek_search/mek_calendar_search.py --limit 500 --output /Users/oraisz/code/largeprojects/literatureclock/scrapers/mek_search/mek_calendar_search_results.jsonl`
2. Create calendar tables:
   - `npm --prefix /Users/oraisz/code/largeprojects/literatureclock/grading-app run migrate:calendar`
3. Seed calendar entries:
   - `DATABASE_URL=... python3 /Users/oraisz/code/largeprojects/literatureclock/seed_calendar_db.py`
4. AI grade with Gemini:
   - `GEMINI_API_KEY=... BUDGET_USD=2 python3 /Users/oraisz/code/largeprojects/literatureclock/calendar_ai_grader.py`
5. Open grader app and switch to `Date Mode`.
