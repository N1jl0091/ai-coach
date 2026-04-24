from app.db.database import get_connection

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS athlete_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strava_athlete_id TEXT UNIQUE,
        access_token TEXT,
        refresh_token TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS training_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strava_activity_id TEXT UNIQUE,
        athlete_id TEXT,
        name TEXT,
        distance REAL,
        moving_time INTEGER,
        sport_type TEXT,
        start_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()
