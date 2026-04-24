from app.db.database import get_connection


def init_db(conn):
    cur = conn.cursor()

    # Unified athlete table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS athlete_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        strava_athlete_id TEXT UNIQUE,
        telegram_id TEXT UNIQUE,

        access_token TEXT,
        refresh_token TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Activity storage (structured but flexible JSON)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS training_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        strava_activity_id TEXT UNIQUE,
        athlete_id TEXT,

        name TEXT,
        sport_type TEXT,

        distance REAL,
        moving_time INTEGER,

        start_date TEXT,

        metrics_json TEXT,   -- key: ALL structured data goes here (splits, power, HR, etc)

        raw_json TEXT,       -- full Strava payload backup

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()