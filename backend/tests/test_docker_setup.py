"""Guards the local Postgres contract that later tasks (db layer, CI) depend on."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_env_example_defines_database_url():
    text = (REPO_ROOT / ".env.example").read_text()
    assert "DATABASE_URL=postgresql://gym:gym@localhost:5432/gym_tracker" in text


def test_compose_runs_postgres_with_named_volume():
    text = (REPO_ROOT / "docker-compose.yml").read_text()
    assert "postgres:16" in text
    assert "gym_pgdata:" in text
    assert '"5432:5432"' in text
