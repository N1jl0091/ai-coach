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
    token_url = "https://www.strava.com/oauth/token"

    response = requests.post(token_url, data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code"
    })

    data = response.json()

    if "access_token" not in data:
        return {
            "status": "error",
            "message": "Strava authentication failed",
            "details": data
        }

    athlete = data.get("athlete", {})

    return {
        "status": "connected",
        "athlete_id": athlete.get("id"),
        "access_token": data.get("access_token"),
        "refresh_token": data.get("refresh_token"),
    }
