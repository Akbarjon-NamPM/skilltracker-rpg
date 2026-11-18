import os
import sqlite3

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
IS_PG = bool(DATABASE_URL)

if IS_PG:
    import psycopg2
    import psycopg2.extras
    IntegrityError = psycopg2.IntegrityError
else:
    IntegrityError = sqlite3.IntegrityError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Vercel's filesystem is read-only except /tmp (and /tmp is wiped), so SQLite
# there is only a demo fallback. Set DATABASE_URL for real persistence.
SQLITE_PATH = "/tmp/project.db" if os.environ.get("VERCEL") else os.path.join(BASE_DIR, "project.db")


class DB:
    def __init__(self):
        if IS_PG:
            self.conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            self.conn = sqlite3.connect(SQLITE_PATH)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")

    def execute(self, sql, params=()):
        if IS_PG:
            sql = sql.replace("?", "%s")
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return cur

    def all(self, sql, params=()):
        return [dict(r) for r in self.execute(sql, params).fetchall()]

    def one(self, sql, params=()):
        row = self.execute(sql, params).fetchone()
        return dict(row) if row else None

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def init_db():
    pk = "SERIAL PRIMARY KEY" if IS_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"
    db = DB()
    db.execute(f"""CREATE TABLE IF NOT EXISTS users (
        id {pk},
        username TEXT NOT NULL UNIQUE,
        hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    db.execute(f"""CREATE TABLE IF NOT EXISTS skills (
        id {pk},
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        description TEXT,
        level INTEGER DEFAULT 1,
        current_xp INTEGER DEFAULT 0,
        xp_to_next_level INTEGER DEFAULT 100)""")
    db.execute(f"""CREATE TABLE IF NOT EXISTS habits (
        id {pk},
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        frequency TEXT DEFAULT 'daily',
        xp_reward INTEGER DEFAULT 25,
        streak INTEGER DEFAULT 0,
        last_completed TEXT)""")
    db.execute(f"""CREATE TABLE IF NOT EXISTS habit_logs (
        id {pk},
        habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        completed_date TEXT NOT NULL)""")
    db.commit()

    # Migration for databases created with the old schema (no last_completed)
    if IS_PG:
        db.execute("ALTER TABLE habits ADD COLUMN IF NOT EXISTS last_completed TEXT")
    else:
        cols = [r["name"] for r in db.execute("PRAGMA table_info(habits)").fetchall()]
        if "last_completed" not in cols:
            db.execute("ALTER TABLE habits ADD COLUMN last_completed TEXT")
    db.execute("""UPDATE habits SET last_completed =
        (SELECT MAX(completed_date) FROM habit_logs WHERE habit_logs.habit_id = habits.id)
        WHERE last_completed IS NULL""")
    db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_habit_logs_once
        ON habit_logs (habit_id, completed_date)""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_skills_user ON skills (user_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_habits_user ON habits (user_id)")
    db.commit()
    db.close()
