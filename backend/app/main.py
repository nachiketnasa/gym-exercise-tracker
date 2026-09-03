from fastapi import FastAPI

from app.routers import exercises, sessions

app = FastAPI(title="Gym Exercise Tracker API")

app.include_router(exercises.router)
app.include_router(sessions.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
