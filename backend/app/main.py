from fastapi import FastAPI

from app.routers import exercises, goals, sessions

app = FastAPI(title="Gym Exercise Tracker API")

app.include_router(exercises.router)
app.include_router(sessions.router)
app.include_router(goals.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
