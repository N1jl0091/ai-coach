from app.db.database import get_connection


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Stores Strava athlete OAuth info
    cur.execute("""
    CREATE TABLE IF NOT EXISTS athlete_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strava_athlete_id TEXT UNIQUE,
        access_token TEXT,
        refresh_token TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Stores ALL activities (runs, rides, gym, etc.)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strava_activity_id TEXT UNIQUE,
        athlete_id TEXT,
        name TEXT,
        type TEXT,
        distance REAL,
        moving_time INTEGER,
        start_date TEXT,
        average_speed REAL,
        average_heartrate REAL,
        average_watts REAL,
        raw_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()