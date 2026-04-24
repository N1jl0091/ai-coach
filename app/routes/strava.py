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
    try:
        payload = await request.json()
        print("\n--- WEBHOOK RECEIVED ---")
        print(payload)

        # Step 1: Validate type
        if payload.get("object_type") != "activity":
            print("IGNORED: not an activity")
            return {"status": "ignored"}

        activity_id = payload.get("object_id")
        athlete_id = payload.get("owner_id")
        aspect_type = payload.get("aspect_type")

        print(f"Activity ID: {activity_id}")
        print(f"Athlete ID: {athlete_id}")
        print(f"Aspect Type: {aspect_type}")

        # Step 2: DB lookup
        conn = get_connection()
        cur = conn.cursor()

        print("Looking up athlete in DB...")

        cur.execute("""
            SELECT access_token
            FROM athlete_profile
            WHERE strava_athlete_id = ?
        """, (str(athlete_id),))

        row = cur.fetchone()

        if not row:
            print("ERROR: Athlete not found in DB")
            return {"error": "athlete not found"}

        access_token = row[0]
        print("Access token found")

        # Step 3: Fetch activity from Strava
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

        # Step 4: Store in DB
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
            str(athlete_id),
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
