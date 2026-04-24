from fastapi import APIRouter, Request
import os
import requests

router = APIRouter()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def send_message(chat_id: int, text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })

@router.post("/telegram/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()

    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if chat_id and text:
        send_message(chat_id, f"Received: {text}")

    return {"ok": True}
