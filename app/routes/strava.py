from fastapi import APIRouter, Request
import requests
import os

from app.db.database import get_connection

router = APIRouter()

# ---- CONFIG ----
CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
REDIRECT_URI = "https://ai-coach-production-06db.up.railway.app/strava/callback"


# =========================
# STRAVA OAUTH
# =========================

@router.get("/strava/login")
def login():
    return {
        "url": (
            f"https://www.strava.com/oauth/authorize"
            f"?client_id={CLIENT_ID}"
            f"&response_type=code"
            f"&redirect_uri={REDIRECT_URI}"
            f"&approval_prompt=force"
            f"&scope=read,activity:read"
        )
    }


@router.get("/strava/callback")
def callback(code: str):
    print("\n--- STRAVA CALLBACK ---")

    token_url = "https://www.strava.com/oauth/token"

    response = requests.post(token_url, data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code"
    })

    data = response.json()
    print("Token response:", data)

    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    athlete = data.get("athlete")

    if not athlete:
        print("ERROR: No athlete returned from Strava")
        return {"error": "no athlete returned"}

    athlete_id = str(athlete.get("id"))
    print("Saving athlete:", athlete_id)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO athlete_profile (
            strava_athlete_id,
            access_token,
            refresh_token
        ) VALUES (?, ?, ?)
    """, (athlete_id, access_token, refresh_token))

    conn.commit()
    conn.close()

    print("SUCCESS: Athlete stored")

    return {
        "status": "connected",
        "athlete_id": athlete_id
    }


# =========================
# WEBHOOK VERIFICATION (GET)
# =========================

@router.get("/strava/webhook")
def verify(request: Request):
    params = dict(request.query_params)

    if "hub.challenge" in params:
        print("Webhook verified by Strava")
        return {"hub.challenge": params["hub.challenge"]}

    return {"status": "ok"}


# =========================
# WEBHOOK EVENTS (POST)
# =========================

@router.post("/strava/webhook")
async def strava_webhook(request: Request):
    try:
        payload = await request.json()

        print("\n--- WEBHOOK RECEIVED ---")
        print(payload)

        # Validate event type
        if payload.get("object_type") != "activity":
            print("IGNORED: Not an activity")
            return {"status": "ignored"}

        activity_id = payload.get("object_id")
        athlete_id = str(payload.get("owner_id"))
        aspect_type = payload.get("aspect_type")

        print(f"Activity ID: {activity_id}")
        print(f"Athlete ID: {athlete_id}")
        print(f"Aspect Type: {aspect_type}")

        # DB lookup
        conn = get_connection()
        cur = conn.cursor()

        print("Looking up athlete in DB...")

        cur.execute("""
            SELECT access_token
            FROM athlete_profile
            WHERE strava_athlete_id = ?
        """, (athlete_id,))

        row = cur.fetchone()

        if not row:
            print("ERROR: Athlete not found in DB")
            return {"error": "athlete not found"}

        access_token = row[0]
        print("Access token found")

        # Fetch activity
        headers = {"Authorization": f"Bearer {access_token}"}

        print("Fetching activity from Strava API...")

        r = requests.get(
            f"https://www.strava.com/api/v3/activities/{activity_id}",
            headers=headers
        )

        print(f"Strava response status: {r.status_code}")

        if r.status_code != 200:
            print("ERROR: Failed to fetch activity")
            print(r.text)
            return {"error": "strava fetch failed"}

        activity = r.json()

        print("Activity fetched:")
        print(activity.get("name"), activity.get("sport_type"))

        # Store in DB
        print("Storing activity in DB...")

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
            athlete_id,
            activity.get("name"),
            activity.get("distance"),
            activity.get("moving_time"),
            activity.get("sport_type"),
            activity.get("start_date")
        ))

        conn.commit()
        conn.close()

        print("SUCCESS: Activity stored")

        return {"status": "stored", "activity_id": activity_id}

    except Exception as e:
        print("FATAL ERROR:", str(e))
        return {"error": "internal failure"}
