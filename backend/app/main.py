from fastapi import FastAPI

app = FastAPI(title="Gym Exercise Tracker API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
