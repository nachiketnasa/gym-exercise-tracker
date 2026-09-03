# Frontend

The Gym Exercise Tracker web client: React + TypeScript, built with [Vite],
tested with [Vitest] + [Testing Library].

Navigation shell plus product screens (see [`../_docs/tasks.md`](../_docs/tasks.md)).

## Routing & layout

Client-side routing uses `react-router-dom`. Routes:

| Path                      | Screen          |
| ------------------------- | --------------- |
| `/`                       | Log Workout     |
| `/history`                | History         |
| `/exercises/:exerciseId`  | Exercise Detail |
| `/goals`                  | Goals           |
| anything else             | Not Found       |

`src/layout/Layout.tsx` is the persistent frame (header + primary nav) that
wraps every route via `<Outlet />`. The active nav item is marked with
`aria-current="page"` (via `NavLink`).

Responsive nav: the breakpoint is **768px**. At >= 768px the nav is a normal
horizontal nav in the header; below 768px it renders as a **fixed bottom nav
bar**. Only CSS (a media query in `src/layout/Layout.css`) changes — the markup
is identical at both sizes.

`<BrowserRouter>` wraps `<App />` in `src/main.tsx`; tests wrap `<App />` in
`<MemoryRouter>`.

## Requirements

- Node 20 LTS or newer (`.nvmrc` pins the version used here; also enforced by
  `package.json` `engines`)
- npm (the committed `package-lock.json` is the source of truth)

## Commands

Run all commands from `frontend/`.

```sh
npm install     # install dependencies
npm run dev     # start the Vite dev server (http://localhost:5173)
npm test        # run the Vitest suite once (non-watch) and exit
npm run build   # type-check with tsc and produce a production build in dist/
```

`npm run preview` serves the built `dist/` locally, and `npm run lint` runs
oxlint (both shipped by the Vite template).

## Configuration

| Env var             | Default                 | Purpose                     |
| ------------------- | ----------------------- | --------------------------- |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Base URL of the backend API |

Copy `.env.example` to `.env` (or `.env.local`) to override it. It is unset by
default, so the client falls back to `http://localhost:8000`.

## API client

`src/api/` holds the typed backend client — a thin wrapper over the native
`fetch` (no HTTP library):

- `src/api/types.ts` — every request and response type. Types for endpoints
  whose backend is not built yet are written against the documented contracts
  and marked `provisional` in comments.
- `src/api/client.ts` — one function per endpoint (exercises, sessions, history,
  entries, PRs, goals, progress), plus `API_BASE_URL`, the `ApiError` type, and
  `toQueryString`.
- `src/api/client.test.ts` — tests with a mocked `fetch`.

Every function returns a typed `Promise` and rejects with an `ApiError` on
failure. `ApiError.kind` is `'network'` for a transport failure or `'http'` for
a completed non-2xx response (which also carries `.status` and the parsed
`.body`). Empty bodies (204) resolve without error.

## Layout

- `src/main.tsx` — entry point, mounts `<App />` inside `<BrowserRouter>`
- `src/App.tsx` — the route table
- `src/App.test.tsx` — routing/nav tests
- `src/layout/` — the persistent layout (`Layout.tsx`, `Layout.css`)
- `src/screens/` — one component per screen (`LogWorkout`, `History`,
  `ExerciseDetail`, `Goals`, `NotFound`) plus co-located `*.test.tsx`
- `src/setupTests.ts` — registers `@testing-library/jest-dom` matchers and
  Testing Library's per-test cleanup
- `src/api/` — the typed backend API client (see "API client" above)
- `src/vite-env.d.ts` — Vite client types + `VITE_API_BASE_URL` typing
- `vite.config.ts` — Vite + Vitest config (`jsdom` test environment)

[Vite]: https://vite.dev/
[Vitest]: https://vitest.dev/
[Testing Library]: https://testing-library.com/docs/react-testing-library/intro/
