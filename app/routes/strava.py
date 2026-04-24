from fastapi import APIRouter, Request
import requests
import json

from app.db.database import get_connection

router = APIRouter()


# -------------------------
# WEBHOOK VERIFICATION
# -------------------------
@router.get("/strava/webhook")
def verify(request: Request):
    params = dict(request.query_params)

    if "hub.challenge" in params:
        print("STRAVA VERIFY OK")
        return {"hub.challenge": params["hub.challenge"]}

    return {"status": "ok"}


# -------------------------
# WEBHOOK EVENT HANDLER
# -------------------------
@router.post("/strava/webhook")
async def strava_webhook(request: Request):

    try:
        payload = await request.json()

        print("\n--- STRAVA WEBHOOK ---")
        print(json.dumps(payload, indent=2))

        # Ignore non-activity events
        if payload.get("object_type") != "activity":
            print("Ignored: non-activity event")
            return {"status": "ignored"}

        activity_id = payload.get("object_id")
        athlete_id = payload.get("owner_id")

        print(f"Activity ID: {activity_id}")
        print(f"Athlete ID: {athlete_id}")

        conn = get_connection()
        cur = conn.cursor()

        print("DB: searching athlete...")

        cur.execute("""
            SELECT access_token
            FROM athlete_profile
            WHERE strava_athlete_id = ?
        """, (str(athlete_id),))

        row = cur.fetchone()

        if not row:
            print("ERROR: athlete not found in DB")
            return {"error": "athlete not found"}

        access_token = row[0]
        print("Access token found")

        # -------------------------
        # FETCH FULL ACTIVITY
        # -------------------------
        headers = {"Authorization": f"Bearer {access_token}"}

        print("Fetching Strava activity...")

        r = requests.get(
            f"https://www.strava.com/api/v3/activities/{activity_id}",
            headers=headers
        )

        if r.status_code != 200:
            print("ERROR: Strava API failed")
            print(r.text)
            return {"error": "strava fetch failed"}

        activity = r.json()

        print("Activity received:")
        print(activity.get("name"), activity.get("sport_type"))

        # -------------------------
        # EXTRACT AI-USEFUL METRICS
        # -------------------------
        metrics = {
            "average_speed": activity.get("average_speed"),
            "max_speed": activity.get("max_speed"),
            "average_watts": activity.get("average_watts"),
            "normalized_power": activity.get("weighted_average_watts"),
            "average_heartrate": activity.get("average_heartrate"),
            "splits": activity.get("splits_metric"),
        }

        # -------------------------
        # STORE IN DB
        # -------------------------
        print("Saving to DB...")

        cur.execute("""
            INSERT OR REPLACE INTO training_log (
                strava_activity_id,
                athlete_id,
                name,
                sport_type,
                distance,
                moving_time,
                start_date,
                metrics_json,
                raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(activity_id),
            str(athlete_id),
            activity.get("name"),
            activity.get("sport_type"),
            activity.get("distance"),
            activity.get("moving_time"),
            activity.get("start_date"),
            json.dumps(metrics),
            json.dumps(activity)
        ))

        conn.commit()
        conn.close()

        print("SUCCESS: activity stored")

        return {
            "status": "stored",
            "activity_id": activity_id
        }

    except Exception as e:
        print("FATAL ERROR:", str(e))
        return {"error": str(e)}

@router.get("/strava/callback")
def callback(code: str):

    token_url = "https://www.strava.com/oauth/token"

    res = requests.post(token_url, data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code"
    })

    token_data = res.json()

    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    athlete = token_data["athlete"]

    strava_athlete_id = athlete["id"]

    print("OAuth success for athlete:", strava_athlete_id)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO athlete_profile (
            strava_athlete_id,
            access_token,
            refresh_token
        ) VALUES (?, ?, ?)
    """, (
        str(strava_athlete_id),
        access_token,
        refresh_token
    ))

    conn.commit()
    conn.close()

    return {
        "status": "connected",
        "athlete_id": strava_athlete_id
    }

@router.get("/debug/activities")
def debug_activities():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM activities
        ORDER BY id DESC
        LIMIT 20
    """)

    rows = cur.fetchall()
    conn.close()

    return [dict(row) for row in rows]