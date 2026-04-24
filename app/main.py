from fastapi import FastAPI
from app.routes.health import router as health_router
from app.routes.telegram import router as telegram_router

app = FastAPI()

app.include_router(health_router)
app.include_router(telegram_router)

@app.get("/")
def root():
    return {"status": "ok"}
