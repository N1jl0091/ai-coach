from fastapi import APIRouter, Request
import requests

from app.db.database import get_connection

router = APIRouter()


# ---- WEBHOOK VERIFICATION (GET) ----
@router.get("/strava/webhook")
def verify(request: Request):
    params = dict(request.query_params)

    if "hub.challenge" in params:
        return {"hub.challenge": params["hub.challenge"]}

    return {"status": "ok"}


# ---- WEBHOOK EVENTS (POST) ----
@router.post("/strava/webhook")
async def strava_webhook(request: Request):
    payload = await request.json()

    if payload.get("object_type") != "activity":
        return {"status": "ignored"}

    activity_id = payload.get("object_id")
    athlete_id = payload.get("owner_id")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT access_token
        FROM athlete_profile
        WHERE strava_athlete_id = ?
    """, (str(athlete_id),))

    row = cur.fetchone()

    if not row:
        return {"error": "athlete not found"}

    access_token = row[0]

    headers = {"Authorization": f"Bearer {access_token}"}

    r = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity_id}",
        headers=headers
    )

    activity = r.json()

    cur.execute("""
        INSERT OR REPLACE INTO training_log (
            strava_activity_id,
            athlete_id,
            name,
            distance,
            moving_time,
            sport_type,
            start_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        str(activity_id),
        str(athlete_id),
        activity.get("name"),
        activity.get("distance"),
        activity.get("moving_time"),
        activity.get("sport_type"),
        activity.get("start_date")
    ))

    conn.commit()
    conn.close()

    return {"status": "stored", "activity_id": activity_id}
