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
| Frontend | React (Vite + TypeScript), tested with Vitest    |
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

The test suite uses a separate `gym_tracker_test` database. It is created
automatically the first time you run the tests; to create it by hand:

```sh
docker compose exec -T db psql -U gym -d gym_tracker -c "CREATE DATABASE gym_tracker_test;"
```

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

### Database layer

The engine, `SessionLocal`, `get_session` dependency, and the declarative
`Base` live in `backend/app/db.py`. The connection URL comes entirely from the
`DATABASE_URL` environment variable (see the root `.env` / `.env.example`);
there is no hardcoded fallback, and an unset `DATABASE_URL` raises a clear
error.

Schema is managed with Alembic and applied to the dev database explicitly:

```sh
cd backend
uv run alembic upgrade head          # apply migrations
uv run alembic downgrade base        # roll them all back
uv run alembic history               # list revisions
```

Add a new migration (edit its `upgrade()` / `downgrade()` afterwards):

```sh
uv run alembic revision -m "add exercises table"
# or, once models exist, autogenerate from metadata:
uv run alembic revision --autogenerate -m "add exercises table"
```

### Running the tests

Tests need Postgres running (`docker compose up -d db` from the repo root) and
a root `.env` with `DATABASE_URL` (`cp .env.example .env`).

They run against a **separate** database — `gym_tracker_test` by default
(the `DATABASE_URL` name plus a `_test` suffix), or `TEST_DATABASE_URL` if you
set it in `.env`. That database is created and migrated to `head`
automatically on first run, so nothing else is needed:

```sh
cd backend
uv run pytest
```

Each test runs inside a transaction that is rolled back on teardown, so the
test database stays empty between runs.

## Frontend

React (Vite + TypeScript) app under `frontend/`. Currently the app shell only:
a single placeholder page with a passing Vitest + Testing Library test. All
commands run from `frontend/` (needs Node 20 LTS or newer — see `frontend/.nvmrc`):

```sh
cd frontend
npm install       # install dependencies
npm run dev       # start the Vite dev server (http://localhost:5173)
npm test          # run the Vitest suite once (non-watch) and exit
npm run build     # type-check and produce a production build in dist/
```

See [`frontend/README.md`](frontend/README.md) for details.
