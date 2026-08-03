import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash
from labs import LABS

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "app.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS lab (
    id   INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entry (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    lab_id  INTEGER NOT NULL REFERENCES lab(id),
    year    INTEGER NOT NULL,
    month   INTEGER NOT NULL,
    day     INTEGER NOT NULL,
    fr      INTEGER NOT NULL DEFAULT 0,
    jlh     INTEGER NOT NULL DEFAULT 0,
    drs     REAL    NOT NULL DEFAULT 0,
    UNIQUE(lab_id, year, month, day)
);

CREATE TABLE IF NOT EXISTS keterangan (
    lab_id  INTEGER NOT NULL REFERENCES lab(id),
    year    INTEGER NOT NULL,
    month   INTEGER NOT NULL,
    note    TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (lab_id, year, month)
);

CREATE TABLE IF NOT EXISTS photo (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    filename   TEXT NOT NULL,
    event_date TEXT NOT NULL,
    lab_id     INTEGER REFERENCES lab(id),
    caption    TEXT NOT NULL DEFAULT '',
    uploaded_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS admin_user (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    pw_hash  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS holiday (
    date        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    is_national INTEGER NOT NULL DEFAULT 1,
    source      TEXT NOT NULL DEFAULT 'manual',
    synced_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS detail (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    lab_id   INTEGER NOT NULL REFERENCES lab(id),
    year     INTEGER NOT NULL,
    month    INTEGER NOT NULL,
    day      INTEGER NOT NULL,
    users    TEXT NOT NULL DEFAULT '',
    jabatan  TEXT NOT NULL DEFAULT '',
    activity TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_entry_period  ON entry(year, month);
CREATE INDEX IF NOT EXISTS idx_photo_date    ON photo(event_date);
CREATE INDEX IF NOT EXISTS idx_photo_lab     ON photo(lab_id, event_date);
CREATE INDEX IF NOT EXISTS idx_detail_period ON detail(year, month);
CREATE INDEX IF NOT EXISTS idx_detail_cell   ON detail(lab_id, year, month, day);
"""


def get_conn():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(default_admin_user="admin", default_admin_pw="admin"):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        # Migration: add jabatan column to existing detail tables (schema evolved after v3).
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(detail)")}
        if "jabatan" not in cols:
            conn.execute("ALTER TABLE detail ADD COLUMN jabatan TEXT NOT NULL DEFAULT ''")
        for lab_id, code, name in LABS:
            conn.execute(
                "INSERT INTO lab (id, code, name) VALUES (?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET code=excluded.code, name=excluded.name",
                (lab_id, code, name),
            )
        row = conn.execute("SELECT COUNT(*) c FROM admin_user").fetchone()
        if row["c"] == 0:
            conn.execute(
                "INSERT INTO admin_user (username, pw_hash) VALUES (?,?)",
                (default_admin_user, generate_password_hash(default_admin_pw)),
            )
        conn.commit()
