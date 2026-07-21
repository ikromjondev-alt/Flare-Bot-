import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "bot_database.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def list_guild_ids():
    conn = get_conn()
    ids = set()
    for table in ("guild_settings", "autorole_config", "log_config", "warns", "mutes"):
        try:
            rows = conn.execute(f"SELECT DISTINCT guild_id FROM {table}").fetchall()
            ids.update(r["guild_id"] for r in rows)
        except sqlite3.OperationalError:
            pass
    conn.close()
    return sorted(ids)


def get_guild_settings(guild_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM guild_settings WHERE guild_id=?", (guild_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}


def update_guild_settings(guild_id, **fields):
    conn = get_conn()
    existing = conn.execute("SELECT guild_id FROM guild_settings WHERE guild_id=?", (guild_id,)).fetchone()
    if existing:
        set_clause = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE guild_settings SET {set_clause} WHERE guild_id=?", (*fields.values(), guild_id))
    else:
        cols = ", ".join(["guild_id"] + list(fields.keys()))
        placeholders = ", ".join(["?"] * (len(fields) + 1))
        conn.execute(f"INSERT INTO guild_settings ({cols}) VALUES ({placeholders})", (guild_id, *fields.values()))
    conn.commit()
    conn.close()


def get_autorole_config(guild_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM autorole_config WHERE guild_id=?", (guild_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}


def update_autorole_config(guild_id, **fields):
    conn = get_conn()
    existing = conn.execute("SELECT guild_id FROM autorole_config WHERE guild_id=?", (guild_id,)).fetchone()
    if existing:
        set_clause = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE autorole_config SET {set_clause} WHERE guild_id=?", (*fields.values(), guild_id))
    else:
        cols = ", ".join(["guild_id"] + list(fields.keys()))
        placeholders = ", ".join(["?"] * (len(fields) + 1))
        conn.execute(f"INSERT INTO autorole_config ({cols}) VALUES ({placeholders})", (guild_id, *fields.values()))
    conn.commit()
    conn.close()


def get_log_channel(guild_id):
    conn = get_conn()
    row = conn.execute("SELECT log_channel_id FROM log_config WHERE guild_id=?", (guild_id,)).fetchone()
    conn.close()
    return row["log_channel_id"] if row else None


def set_log_channel(guild_id, channel_id):
    conn = get_conn()
    conn.execute(
        """INSERT INTO log_config (guild_id, log_channel_id) VALUES (?, ?)
           ON CONFLICT(guild_id) DO UPDATE SET log_channel_id=excluded.log_channel_id""",
        (guild_id, channel_id),
    )
    conn.commit()
    conn.close()


def list_warns(guild_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, user_id, moderator_id, reason, created_at FROM warns WHERE guild_id=? ORDER BY id DESC",
        (guild_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_warn(warn_id):
    conn = get_conn()
    conn.execute("DELETE FROM warns WHERE id=?", (warn_id,))
    conn.commit()
    conn.close()


def list_allowed_domains(guild_id):
    conn = get_conn()
    rows = conn.execute("SELECT domain FROM allowed_domains WHERE guild_id=?", (guild_id,)).fetchall()
    conn.close()
    return [r["domain"] for r in rows]


def add_allowed_domain(guild_id, domain):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO allowed_domains (guild_id, domain) VALUES (?, ?)", (guild_id, domain.lower()))
    conn.commit()
    conn.close()


def remove_allowed_domain(guild_id, domain):
    conn = get_conn()
    conn.execute("DELETE FROM allowed_domains WHERE guild_id=? AND domain=?", (guild_id, domain.lower()))
    conn.commit()
    conn.close()
