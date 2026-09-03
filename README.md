# Gym Exercise Tracker

Responsive web app for tracking gym workouts — logging, progress charts, personal
records, and goals. Single-user for v1, designed to scale to multi-user later.

- Product scope: [`_docs/plan.md`](_docs/plan.md)
- Task backlog: [`_docs/tasks.md`](_docs/tasks.md) (mirrored to GitHub issues)
- Working process: [`_docs/process.md`](_docs/process.md)

## Stack

| Layer    | Tech                                             |
| -------- | ----------------------------------------------- |
| Backend  | FastAPI (Python 3.12), managed with [uv]        |
| Frontend | React (Vite + TypeScript) — not scaffolded yet  |
| Database | PostgreSQL 16 (local via Docker Compose)        |

[uv]: https://docs.astral.sh/uv/

## Database

Local Postgres runs in Docker Compose. Run from the repo root:

```sh
cp .env.example .env      # first time only
docker compose up -d db    # start Postgres in the background
docker compose down        # stop it (data is kept in the gym_pgdata volume)
docker compose down -v     # stop it and delete the data volume
```

Connection string (also in `.env.example`):

```
postgresql://gym:gym@localhost:5432/gym_tracker
```

The backend reads it from the `DATABASE_URL` environment variable.

## Backend

All commands run from `backend/`.

```sh
cd backend
uv sync                              # install dependencies
uv run pytest                        # run the whole test suite
uv run pytest tests/test_health.py   # run one test file
uv run fastapi dev app/main.py       # run the dev server (http://127.0.0.1:8000)
```

`GET /health` returns `{"status": "ok"}`.

## Frontend

Not yet scaffolded — see task 4 in the backlog.
