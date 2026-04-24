from fastapi import APIRouter, Request
import requests
import json
import logging

from app.db.database import get_connection

router = APIRouter()

logging.basicConfig(level=logging.INFO)


# ---------------------------
# STRAVA LOGIN
# ---------------------------
@router.get("/strava/login")
def login():
    client_id = "167015"

    return {
        "url": (
            "https://www.strava.com/oauth/authorize"
            f"?client_id={client_id}"
            "&response_type=code"
            "&redirect_uri=https://ai-coach-production-06db.up.railway.app/strava/callback"
            "&approval_prompt=force"
            "&scope=read,activity:read_all"
        )
    }


# ---------------------------
# STRAVA CALLBACK (IMPORTANT FIX)
# ---------------------------
@router.get("/strava/callback")
def callback(code: str):
    token_url = "https://www.strava.com/oauth/token"

    res = requests.post(token_url, data={
        "client_id": "167015",
        "client_secret": "YOUR_CLIENT_SECRET",
        "code": code,
        "grant_type": "authorization_code"
    })

    data = res.json()

    athlete_id = data["athlete"]["id"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO athlete_profile
        (strava_athlete_id, access_token, refresh_token)
        VALUES (?, ?, ?)
    """, (
        str(athlete_id),
        data["access_token"],
        data["refresh_token"]
    ))

    conn.commit()
    conn.close()

    logging.info(f"Stored athlete {athlete_id}")

    return {"status": "ok"}


# ---------------------------
# WEBHOOK VERIFY (Strava requirement)
# ---------------------------
@router.get("/strava/webhook")
def verify(request: Request):
    params = dict(request.query_params)

    if "hub.challenge" in params:
        return {"hub.challenge": params["hub.challenge"]}

    return {"status": "ok"}


# ---------------------------
# WEBHOOK INGESTION (CORE SYSTEM)
# ---------------------------
@router.post("/strava/webhook")
async def webhook(request: Request):

    payload = await request.json()

    logging.info(f"WEBHOOK: {json.dumps(payload)}")

    if payload.get("object_type") != "activity":
        return {"status": "ignored"}

    activity_id = payload["object_id"]
    athlete_id = payload["owner_id"]

    conn = get_connection()
    cur = conn.cursor()

    # ---------------------------
    # 1. GET ATHLETE TOKEN
    # ---------------------------
    cur.execute("""
        SELECT access_token
        FROM athlete_profile
        WHERE strava_athlete_id = ?
    """, (str(athlete_id),))

    row = cur.fetchone()

    if not row:
        logging.error("Athlete not found")
        return {"error": "athlete not found"}

    access_token = row["access_token"]

    # ---------------------------
    # 2. FETCH FULL ACTIVITY
    # ---------------------------
    headers = {"Authorization": f"Bearer {access_token}"}

    r = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity_id}",
        headers=headers
    )

    if r.status_code != 200:
        logging.error(r.text)
        return {"error": "failed to fetch activity"}

    activity = r.json()

    # ---------------------------
    # 3. STORE ACTIVITY (FULL RAW JSON INCLUDED)
    # ---------------------------
    cur.execute("""
        INSERT OR REPLACE INTO activities (
            strava_activity_id,
            athlete_id,
            name,
            type,
            distance,
            moving_time,
            start_date,
            average_speed,
            average_heartrate,
            average_watts,
            raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(activity_id),
        str(athlete_id),
        activity.get("name"),
        activity.get("type"),
        activity.get("distance"),
        activity.get("moving_time"),
        activity.get("start_date"),
        activity.get("average_speed"),
        activity.get("average_heartrate"),
        activity.get("average_watts"),
        json.dumps(activity)
    ))

    conn.commit()
    conn.close()

    logging.info(f"Stored activity {activity_id}")

    return {"status": "stored"}
        
