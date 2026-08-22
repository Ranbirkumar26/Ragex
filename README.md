# Ragex Pricing Guardrail Demo

Local demo for pricing decisions, real-time guardrail checks, regret scoring, and grounded policy explanations.

## Run backend

```bash
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.api.main:app --reload --port 8000
```

The backend defaults to static CSV data under `data/exports`. If `REPOSITORY_MODE=auto` and Supabase env vars are present, it uses Supabase through the PostgREST Data API instead.

If Management API keys are unavailable, set `SUPABASE_DB_URL` instead. The backend then uses direct Supabase Postgres while keeping the same repository interface.

Set `VECTOR_BACKEND=chroma` to persist the local policy vector store under `data/chroma`; otherwise the backend uses the same pinned 768-dimensional embedding path in memory.

## Run dashboard

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:3000`.

## Supabase database

```bash
cp .env.example .env
# set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
# or set SUPABASE_DB_URL
supabase db push
cd backend
.venv/bin/python scripts/seed_supabase.py
```

Schema lives in `supabase/migrations`. Backend uses only `SUPABASE_SERVICE_ROLE_KEY`; no Supabase secret is exposed to the Next.js dashboard.

## Tests

```bash
cd backend
.venv/bin/pytest

cd ../web
npm test
```
