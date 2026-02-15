# Korea Local Finder (Naver Blog)

Production-focused starter app for finding **popular local places in Korea** from **Naver blog posts**.

## What this app does
- You type in **English**.
- App translates query to **Korean**.
- Searches Naver blogs for city + categories.
- De-duplicates overlapping posts.
- Ranks with a **popularity proxy**:
  - repeated place mentions,
  - recency,
  - hot-keyword signals.
- Returns results translated back to English.
- Includes map links and neighborhood/address hints.
- Supports **offline/mock mode** for environments where external API access is blocked.

## Required credentials
You need Naver Search API credentials for live mode:
- `NAVER_CLIENT_ID`
- `NAVER_CLIENT_SECRET`

> Keep these in environment variables (or local `.env`) and **never commit real secrets**.

## Quick start
```bash
export NAVER_CLIENT_ID=your_client_id
export NAVER_CLIENT_SECRET=your_client_secret
python app.py
```

Open: `http://localhost:5000`

## API
`GET /api/search`

### Query params
- `q` (required): english or korean query
- `city`: `seoul` or `busan` (default `seoul`)
- `categories`: comma-separated list from `restaurants,cafes,bars,activities,gyms`
- `limit`: max returned ranked rows (1-50)
- `mock`: `1` to force offline mock response
- `fallback`: `1` (default) to auto-fallback to mock if live mode fails, `0` to return live error

Example:
```bash
curl "http://localhost:5000/api/search?q=popular%20cafes&city=seoul&categories=restaurants,cafes,bars,activities,gyms&limit=10"
```

Force mock mode:
```bash
curl "http://localhost:5000/api/search?q=popular%20cafes&city=seoul&categories=cafes&mock=1"
```

## How to test
```bash
pytest -q
python -m py_compile app.py core.py
```

## Notes on popularity ranking
Naver blog API does not directly expose a universal "hearts/likes" field for each post in this endpoint, so this app uses a practical proxy score. You can refine this later by integrating additional signals (saved place counts, social metrics, etc.) if your data source expands.
