from fastapi import FastAPI

from app.routers import exercises

app = FastAPI(title="Gym Exercise Tracker API")

app.include_router(exercises.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
