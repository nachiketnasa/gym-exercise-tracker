# Frontend

The Gym Exercise Tracker web client: React + TypeScript, built with [Vite],
tested with [Vitest] + [Testing Library].

This is the app shell only — a single placeholder page. Navigation and the
product screens are added in later tasks (see [`../_docs/tasks.md`](../_docs/tasks.md)).

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

## Layout

- `src/main.tsx` — entry point, mounts `<App />`
- `src/App.tsx` — the root component (placeholder page)
- `src/App.test.tsx` — the one test: renders `<App />` and asserts on its text
- `src/setupTests.ts` — registers `@testing-library/jest-dom` matchers
- `vite.config.ts` — Vite + Vitest config (`jsdom` test environment)

[Vite]: https://vite.dev/
[Vitest]: https://vitest.dev/
[Testing Library]: https://testing-library.com/docs/react-testing-library/intro/
