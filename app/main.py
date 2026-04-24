from fastapi import FastAPI

from app.routes.health import router as health_router
from app.routes.telegram import router as telegram_router
from app.routes.strava import router as strava_router
from app.db.models import init_db

app = FastAPI()   # <-- MUST be first

init_db()

app.include_router(health_router)
app.include_router(telegram_router)
app.include_router(strava_router)


@app.get("/")
def root():
    return {"status": "ok"}
