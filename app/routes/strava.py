#!/usr/bin/env python3

from fastapi import APIRouter, Request
import os
import requests

router = APIRouter()

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")

# 1. Redirect user to Strava auth
@router.get("/strava/login")
def login():
    return {
        "url": f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri=https://ai-coach-production-06db.up.railway.app/strava/callback&approval_prompt=force&scope=read,activity:read"
    }

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

    return response.json()
