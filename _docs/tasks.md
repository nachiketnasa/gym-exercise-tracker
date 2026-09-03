# Gym Exercise Tracker — Task Backlog

Scope and data model live in `_docs/plan.md`. Stack: FastAPI (Python) backend,
React frontend, PostgreSQL database. Each task below is sized for one session and
written to be picked up without reading the others.

Tasks 1–22 are GitHub issues #1–#22. Follow-up issues filed during grooming are
listed here with their issue number in the heading. Once an issue is groomed, its
issue body (four-section template) is the source of truth — the entry here is
just a summary.

## 1. Initialize repository and backend skeleton with a passing test — done (#1)
Goal: A runnable, empty FastAPI project with one green test.
Description: Created `backend/` as a uv-managed FastAPI project with a `GET /health`
endpoint and a pytest suite containing one test that asserts `/health` returns
200. README documents install/test/run; `frontend/` holds a placeholder.

## 2. Set up local PostgreSQL via Docker Compose
Goal: One command brings up a Postgres instance for local development.
Description: Add a `docker-compose.yml` that runs PostgreSQL with a named volume,
sensible default credentials, and a mapped port. Document the connection string
and the up/down commands in the README, and add a `.env.example` with the
database URL variable the backend will read.

## 3. Add database layer and migrations
Goal: The backend can connect to Postgres and apply schema migrations.
Description: Add SQLAlchemy (or SQLModel) with a session/engine module that reads
the database URL from the environment, and configure Alembic for migrations.
Include an initial empty migration and a test that opens a connection and runs a
trivial `SELECT 1` against a test database.

## 4. Scaffold the React frontend with a passing test — groomed (#4)
Goal: A runnable, empty React app with one green test.
Description: Create the `frontend/` project from the Vite `react-ts` template
(npm, committed lockfile, Node 20+), strip it to one placeholder page, and set up
Vitest + Testing Library (jsdom, jest-dom) with one test that renders the root
component and asserts on visible text. Update the README with install/dev/test/
build commands. Full acceptance criteria and constraints are in issue #4.

## 5. Define the Exercise data model and migration
Goal: An `exercises` table exists with the fields v1 needs.
Description: Model an Exercise with name, category (`strength` or `cardio`), a
flag for preset vs. custom, and timestamps. Write the Alembic migration and a
model-level test that creates and reads back an exercise of each category.

## 6. Seed the preset exercise library
Goal: A known set of common exercises is loaded into the database.
Description: Create a seed script (or data migration) that inserts ~15–25 common
exercises (e.g. bench press, squat, deadlift, running, cycling) tagged as
presets, each with the correct category. Make the seed idempotent and add a test
that asserts the expected presets are present after running it.

## 7. Build the Exercise API
Goal: Clients can list exercises and create custom ones.
Description: Add endpoints to list all exercises (presets + custom), fetch one by
id, and create a custom exercise with validation on name and category. Cover the
happy paths and validation errors with API tests. Assumes an `exercises` table
and preset seed already exist.

## 8. Define the Workout Session and Exercise Entry data models
Goal: Tables exist to record a session and the exercises performed in it.
Description: Model a Workout Session (date, optional notes, timestamps) and an
Exercise Entry that links a session to an exercise and stores the metric fields —
strength: sets/reps/weight/unit; cardio: duration/distance/pace. Write the
migration and model tests that create a session with one strength entry and one
cardio entry.

## 9. Build the Workout logging API
Goal: Clients can create a workout session and record exercise entries.
Description: Add endpoints to create a session, add/update/remove entries on it,
and fetch a full session by id. Support both live logging (create empty, append
entries) and after-the-fact entry (create with entries in one request). Cover
with API tests. Assumes the session and entry models exist.

## 10. Build the Workout history API
Goal: Clients can retrieve past sessions in reverse-chronological order.
Description: Add a paginated list endpoint returning session summaries (date,
exercise count, primary lifts) newest-first, with optional date-range filtering.
Add API tests for ordering, pagination, and filtering. Assumes workout sessions
can already be created.

## 11. Implement personal record (PR) auto-calculation
Goal: The system derives best values per exercise, per metric, from logged data.
Description: Add logic that computes PRs (e.g. max weight, max reps at a weight,
best pace, longest distance) from a user's exercise entries, plus an endpoint to
fetch PRs for a given exercise. First resolve the open question in `plan.md`:
whether PRs track multiple metrics per exercise or one primary metric. Cover the
calculation with unit tests over fixture data.

## 12. Define the Goal data model and build the Goals API
Goal: Clients can set, edit, and list target values per exercise.
Description: Model a Goal as one or more target metric values tied to an exercise
(e.g. "bench 200lb x5", "5k under 25min"), with timestamps. Add CRUD endpoints
and API tests. Assumes the `exercises` table exists.

## 13. Build the per-exercise progress API
Goal: Clients can get a time series of a metric for one exercise.
Description: Add an endpoint that returns, for a given exercise and metric, an
ordered series of `(date, value)` points derived from logged entries, suitable
for charting. Support selecting which metric and an optional date range. Cover
with API tests over fixture data.

## 14. Add single-user scoping stub
Goal: Every user-owned row carries an owner id, defaulted to a single local user.
Description: Add a `user_id` column to sessions, goals, and any other user-owned
tables, plus a dependency that resolves the "current user" to a single seeded
local user for now. Keep the API surface unchanged. This isolates the future
multi-user change to auth only. Add tests asserting rows are created with the
owner id.

## 15. Configure app settings, CORS, and error handling
Goal: The backend has centralized config and consistent error responses.
Description: Add a typed settings object (env-driven: database URL, allowed
origins, environment name), enable CORS for the frontend dev origin, and add an
exception handler that returns a consistent JSON error shape for validation and
not-found errors. Add tests for a CORS preflight and a 404 body.

## 16. Build the frontend API client and shared types
Goal: The frontend has one typed module for talking to the backend.
Description: Create an API client wrapping fetch with base-URL config, error
handling, and typed functions for the existing endpoints (exercises, sessions,
history, PRs, goals, progress). Define the request/response types in one place.
Add tests using a mocked fetch. Assumes the backend endpoints exist.

## 17. Build the app navigation shell and responsive layout
Goal: A mobile-friendly frame with routing between the four core screens.
Description: Add routing and a responsive layout (bottom nav or hamburger on
small screens) with placeholder routes for Log Workout, History, Exercise Detail,
and Goals. No data yet — just navigation and layout. Add a test that navigating
changes the visible screen.

## 18. Build the Log Workout screen
Goal: A user can record a workout from the UI, live or after the fact.
Description: Build a screen to pick an exercise (from the preset/custom list or
add custom inline), enter the metric fields appropriate to its category, add
multiple exercises to the session, and save. Handle both starting an empty
session and entering a completed one. Add component tests with a mocked API
client.

## 19. Build the History screen
Goal: A user can browse and open past workout sessions.
Description: Build a reverse-chronological list of past sessions showing date and
a summary, with pagination or infinite scroll, and tapping a session shows its
full details. Add component tests with a mocked API client. Assumes the history
and session-detail endpoints exist.

## 20. Build the Exercise Detail screen
Goal: A user can see progress, PR, and goal for one exercise.
Description: Build a screen showing a progress chart for a selected metric, the
current PR(s), and the active goal for that exercise, with a control to switch
metrics. Use a charting library for the trend line. Add component tests with a
mocked API client. Assumes the progress, PR, and goal endpoints exist.

## 21. Build the Goals screen
Goal: A user can set and edit target values per exercise.
Description: Build a screen listing existing goals and a form to create or edit a
goal for an exercise (target metric values, e.g. weight x reps or a time for a
distance). Add component tests with a mocked API client. Assumes the Goals API
exists.

## 22. Add CI running backend and frontend test suites
Goal: Every push runs both test suites and reports pass/fail.
Description: Add a CI workflow that provisions a Postgres service, installs
backend and frontend dependencies, runs migrations, and executes pytest and the
frontend tests. Fail the build on any failure and document the badge/status in
the README.

## 23. Frontend formatting and lint tooling (#24)
Goal: Consistent, enforceable formatting and linting for the frontend.
Description: Configure Prettier (committed config), review/keep the Vite ESLint
config, and add `lint`, `format`, and `format:check` npm scripts that exit
non-zero on failure, with all existing `frontend/` files passing. Document the
commands in the README. Split out of task 4 during grooming; wiring into CI stays
with task 22.
