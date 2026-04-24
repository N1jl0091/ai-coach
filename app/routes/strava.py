#!/usr/bin/env python3

from fastapi import APIRouter
import os
import requests

router = APIRouter()

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    raise Exception("Missing STRAVA_CLIENT_ID or STRAVA_CLIENT_SECRET")


# 1. Redirect user to Strava auth
@router.get("/strava/login")
def login():
    url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        "&response_type=code"
        "&redirect_uri=https://ai-coach-production-06db.up.railway.app/strava/callback"
        "&approval_prompt=force"
        "&scope=read,activity:read"
    )

    return {"url": url}


# 2. OAuth callback

@router.get("/strava/callback")
def callback(code: str):
    res = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code"
    })

    data = res.json()

    if "access_token" not in data:
        return {"error": "auth_failed", "details": data}

    athlete = data["athlete"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO athlete_profile (
            strava_athlete_id,
            access_token,
            refresh_token
        ) VALUES (?, ?, ?)
    """, (
        str(athlete["id"]),
        data["access_token"],
        data["refresh_token"]
    ))

    conn.commit()
    conn.close()

    return {
        "status": "stored",
        "athlete_id": athlete["id"]
    }

@router.post("/strava/webhook")
async def strava_webhook(request: Request):
    payload = await request.json()

    # Ignore non-activity events
    if payload.get("object_type") != "activity":
        return {"status": "ignored"}

    activity_id = payload.get("object_id")
    athlete_id = payload.get("owner_id")

    conn = get_connection()
    cur = conn.cursor()

    # Get access token
    cur.execute("""
        SELECT access_token
        FROM athlete_profile
        WHERE strava_athlete_id = ?
    """, (str(athlete_id),))

    row = cur.fetchone()

    if not row:
        return {"error": "athlete not found"}

    access_token = row[0]

    # Fetch full activity from Strava API
    headers = {"Authorization": f"Bearer {access_token}"}

    r = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity_id}",
        headers=headers
    )

    activity = r.json()

    # Store training data
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

    return {
        "status": "stored",
        "activity_id": activity_id
    }

from fastapi import Request, APIRouter

router = APIRouter()


# REQUIRED: webhook verification (Strava handshake)
@router.get("/strava/webhook")
def verify(request: Request):
    params = dict(request.query_params)

    # Strava sends this during verification
    if "hub.challenge" in params:
        return {"hub.challenge": params["hub.challenge"]}

    return {"status": "ok"}
