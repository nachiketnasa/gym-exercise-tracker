# Gym Exercise Tracker

[![CI](https://github.com/nachiketnasa/gym-exercise-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/nachiketnasa/gym-exercise-tracker/actions/workflows/ci.yml)

Responsive web app for tracking gym workouts — logging, progress charts, personal
records, and goals. Single-user for v1, designed to scale to multi-user later.

## Continuous integration

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every push and
pull request, as two independent jobs (the workflow is red if either is):

- **Backend** — starts a PostgreSQL 16 service, `uv sync`, applies the Alembic
  migrations against the CI database, then runs `uv run pytest`.
- **Frontend** — `npm ci`, then `npm run lint` (oxlint), `npm test` (Vitest,
  non-watch), and `npm run build`.

Dependency caches are configured for uv and npm. No secrets are needed — the CI
`DATABASE_URL` is defined in the workflow. (A `format:check` step will be added
to the frontend job once the formatter lands in #24.)

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

Interactive API docs (Swagger UI) are served at
[`/docs`](http://127.0.0.1:8000/docs) once the dev server is running.

### Configuration, CORS, and error shape

All backend configuration is read from the environment (and a local `.env`)
through one typed settings object in `backend/app/config.py`
(`pydantic-settings`). Use `get_settings()` for the cached instance. Fields:

| Field          | Env var         | Default                     | Notes |
| -------------- | --------------- | --------------------------- | ----- |
| `database_url` | `DATABASE_URL`  | none (required)             | Unset ⇒ startup fails with an error naming `DATABASE_URL` |
| `cors_origins` | `CORS_ORIGINS`  | `["http://localhost:5173"]` | Override with a comma-separated list or a JSON array |
| `environment`  | `ENVIRONMENT`   | `local`                     | e.g. `local` / `dev` / `prod` |

Every variable is listed in `backend/.env.example`.

`CORSMiddleware` is installed from `settings.cors_origins` (credentials allowed,
common methods and all headers), so the Vite dev server at
`http://localhost:5173` can call the API.

Handled error responses (currently 404 and 422) share one JSON envelope:

```json
{"error": {"code": "not_found", "message": "…", "details": null}}
```

`code` is a stable string (`not_found`, `validation_error`, `conflict`, …).
For a `422` validation error, `details` is the list of per-field errors.

### Exercise API

| Method | Path               | Description                                             |
| ------ | ------------------ | ------------------------------------------------------- |
| GET    | `/exercises`       | List every exercise (presets + custom), ordered by name |
| GET    | `/exercises/{id}`  | Fetch one exercise by id (404 if it does not exist)     |
| POST   | `/exercises`       | Create a custom exercise (`name`, `category`); 409 on a duplicate name (case-insensitive), 422 on invalid input |

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

### Preset exercise library

Once the schema is at `head`, load the built-in library of common exercises
(each stored with `is_preset = true`):

```sh
cd backend
uv run alembic upgrade head       # must run first
uv run python -m app.seed         # insert any missing presets
```

The full list lives in `backend/app/seed.py`. The seed is idempotent: it
matches presets by case-insensitive name, so re-running it inserts nothing,
never duplicates or edits custom exercises, and re-inserts any preset that was
manually deleted. It prints how many rows it inserted and how many already
existed.

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

### Single-user (for now)

The backend is **single-user**: there is exactly one user and every user-owned
row belongs to it. A `users` table exists and `workout_sessions` and `goals`
each carry a non-null `user_id` foreign key to it (the shared exercise library
and exercise entries are not user-scoped). A `current_user` FastAPI dependency
(`backend/app/deps.py`) resolves to that one user and is injected wherever
user-owned rows are created or listed.

The local user (`local@example.com`, id `1` — see `backend/app/users.py`,
`SEED_USER`) is seeded three ways, all idempotent:

- the Alembic migration that adds the `users` table inserts it, so a freshly
  migrated database already has it;
- `uv run python -m app.seed` calls `ensure_seed_user()` before seeding the
  presets;
- the API creates it on startup if it is missing.

Real authentication (login, tokens, resolving `current_user` from the request)
is a later change (#27); only `current_user` has to change, not its call sites.

## Frontend

React (Vite + TypeScript) app under `frontend/`, tested with Vitest + Testing
Library. It has a typed backend API client (`frontend/src/api/`), client-side
routing (`react-router-dom`) with a responsive nav shell, and screens for
logging workouts, history, exercise detail, and goals. Routes and the responsive
breakpoint are documented in [`frontend/README.md`](frontend/README.md). All
commands run from `frontend/` (needs Node 20 LTS or newer — see
`frontend/.nvmrc`):

```sh
cd frontend
npm install       # install dependencies
npm run dev       # start the Vite dev server (http://localhost:5173)
npm test          # run the Vitest suite once (non-watch) and exit
npm run build     # type-check and produce a production build in dist/
```

The client reads the backend base URL from the `VITE_API_BASE_URL` env var
(see `frontend/.env.example`), falling back to `http://localhost:8000`.

See [`frontend/README.md`](frontend/README.md) for details.
