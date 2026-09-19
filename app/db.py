import sqlite3
from pathlib import Path
from .config import DATABASE_PATH

def init_db():
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as con:
        con.execute('''CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            prompt TEXT,
            status TEXT NOT NULL,
            output_path TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        con.commit()

def add_job(user_id, kind, prompt, status="queued"):
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.execute(
            "INSERT INTO jobs(user_id,kind,prompt,status) VALUES(?,?,?,?)",
            (user_id, kind, prompt, status)
        )
        con.commit()
        return cur.lastrowid

def update_job(job_id, status, output_path=None):
    with sqlite3.connect(DATABASE_PATH) as con:
        con.execute(
            "UPDATE jobs SET status=?, output_path=COALESCE(?, output_path) WHERE id=?",
            (status, output_path, job_id)
        )
        con.commit()

def history(user_id, limit=10):
    with sqlite3.connect(DATABASE_PATH) as con:
        return con.execute(
            "SELECT id,kind,status,created_at,output_path FROM jobs "
            "WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
