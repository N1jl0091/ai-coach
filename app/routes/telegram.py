from fastapi import APIRouter, Request
from app.db.database import get_connection

router = APIRouter()

@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")

    if chat_id:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT OR IGNORE INTO athlete_profile (telegram_id)
            VALUES (?)
        """, (str(chat_id),))

        conn.commit()
        conn.close()

    return {"ok": True}
