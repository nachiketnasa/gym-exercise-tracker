Commands

Run from `backend/`:

- `uv sync` - install dependencies
- `uv run pytest` - the whole suite
- `uv run pytest tests/test_health.py` - one test file

Rules

- Dependencies are added in `backend/pyproject.toml`. Do not add one without
  asking
