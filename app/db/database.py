import sqlite3
from pathlib import Path
from app.db.models import init_db

DB_PATH = Path("app.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
