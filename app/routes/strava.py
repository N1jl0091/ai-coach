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
