import sqlite3

DB_PATH = "accounts.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "user_id INTEGER PRIMARY KEY,"
        "label TEXT NOT NULL DEFAULT '',"
        "tos TEXT NOT NULL DEFAULT '',"
        "msg TEXT NOT NULL DEFAULT '',"
        "added_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    cols = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    if "tos" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN tos TEXT NOT NULL DEFAULT ''")
    if "msg" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN msg TEXT NOT NULL DEFAULT ''")
    conn.commit()
    conn.close()


def is_authorized(user_id):
    conn = _connect()
    row = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row is not None


def add_user(user_id, label=""):
    conn = _connect()
    conn.execute(
        "INSERT INTO users (user_id, label) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET label = excluded.label",
        (user_id, label),
    )
    conn.commit()
    conn.close()


def load_authorized():
    conn = _connect()
    rows = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    return [row["user_id"] for row in rows]


def ensure_user(user_id, label=""):
    conn = _connect()
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, label) VALUES (?, ?)",
        (user_id, label),
    )
    conn.commit()
    conn.close()


def remove_user(user_id):
    conn = _connect()
    conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def list_users():
    conn = _connect()
    rows = conn.execute("SELECT * FROM users ORDER BY added_at").fetchall()
    conn.close()
    return rows


def get_user(user_id):
    conn = _connect()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def set_tos(user_id, text):
    conn = _connect()
    conn.execute("UPDATE users SET tos = ? WHERE user_id = ?", (text, user_id))
    conn.commit()
    conn.close()


def set_msg(user_id, text):
    conn = _connect()
    conn.execute("UPDATE users SET msg = ? WHERE user_id = ?", (text, user_id))
    conn.commit()
    conn.close()
