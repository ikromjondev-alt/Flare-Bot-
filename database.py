import aiosqlite
import time
from config import DB_PATH

_db: aiosqlite.Connection | None = None


async def init_db():
    """Создаёт таблицы, если их ещё нет. Вызывается один раз при старте бота."""
    global _db
    _db = await aiosqlite.connect(DB_PATH)
    await _db.executescript(
        """
        CREATE TABLE IF NOT EXISTS warns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT,
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS autorole_config (
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER,
            role_id INTEGER,
            custom_message TEXT,
            enabled INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS log_config (
            guild_id INTEGER PRIMARY KEY,
            log_channel_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            mod_log_channel_id INTEGER,
            report_channel_id INTEGER,
            report_forum_id INTEGER,
            antispam_enabled INTEGER DEFAULT 1,
            language TEXT DEFAULT 'ru',
            warn_limit INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS allowed_domains (
            guild_id INTEGER NOT NULL,
            domain TEXT NOT NULL,
            PRIMARY KEY (guild_id, domain)
        );
        """
    )
    # Миграции для баз, созданных до появления новых колонок
    for stmt in (
        "ALTER TABLE guild_settings ADD COLUMN language TEXT DEFAULT 'ru'",
        "ALTER TABLE guild_settings ADD COLUMN warn_limit INTEGER DEFAULT 0",
        "ALTER TABLE guild_settings ADD COLUMN report_forum_id INTEGER",
    ):
        try:
            await _db.execute(stmt)
        except Exception:
            pass  # колонка уже существует
    await _db.commit()


def get_db() -> aiosqlite.Connection:
    if _db is None:
        raise RuntimeError("База данных ещё не инициализирована — вызовите init_db() при старте бота.")
    return _db


# ---------- WARNS ----------

async def add_warn(guild_id: int, user_id: int, moderator_id: int, reason: str):
    db = get_db()
    await db.execute(
        "INSERT INTO warns (guild_id, user_id, moderator_id, reason, created_at) VALUES (?, ?, ?, ?, ?)",
        (guild_id, user_id, moderator_id, reason, int(time.time())),
    )
    await db.commit()


async def remove_last_warn(guild_id: int, user_id: int) -> bool:
    db = get_db()
    cur = await db.execute(
        "SELECT id FROM warns WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 1",
        (guild_id, user_id),
    )
    row = await cur.fetchone()
    if not row:
        return False
    await db.execute("DELETE FROM warns WHERE id=?", (row[0],))
    await db.commit()
    return True


async def get_warns(guild_id: int, user_id: int):
    db = get_db()
    cur = await db.execute(
        "SELECT moderator_id, reason, created_at FROM warns WHERE guild_id=? AND user_id=? ORDER BY id",
        (guild_id, user_id),
    )
    return await cur.fetchall()


# ---------- AUTOROLE ----------

async def set_autorole_channel(guild_id: int, channel_id: int):
    db = get_db()
    await db.execute(
        """INSERT INTO autorole_config (guild_id, channel_id) VALUES (?, ?)
           ON CONFLICT(guild_id) DO UPDATE SET channel_id=excluded.channel_id""",
        (guild_id, channel_id),
    )
    await db.commit()


async def set_autorole_role(guild_id: int, role_id: int):
    db = get_db()
    await db.execute(
        """INSERT INTO autorole_config (guild_id, role_id) VALUES (?, ?)
           ON CONFLICT(guild_id) DO UPDATE SET role_id=excluded.role_id""",
        (guild_id, role_id),
    )
    await db.commit()


async def set_autorole_message(guild_id: int, message: str):
    db = get_db()
    await db.execute(
        """INSERT INTO autorole_config (guild_id, custom_message) VALUES (?, ?)
           ON CONFLICT(guild_id) DO UPDATE SET custom_message=excluded.custom_message""",
        (guild_id, message),
    )
    await db.commit()


async def set_autorole_enabled(guild_id: int, enabled: bool):
    db = get_db()
    await db.execute(
        """INSERT INTO autorole_config (guild_id, enabled) VALUES (?, ?)
           ON CONFLICT(guild_id) DO UPDATE SET enabled=excluded.enabled""",
        (guild_id, int(enabled)),
    )
    await db.commit()


async def get_autorole_config(guild_id: int):
    db = get_db()
    cur = await db.execute(
        "SELECT channel_id, role_id, custom_message, enabled FROM autorole_config WHERE guild_id=?",
        (guild_id,),
    )
    return await cur.fetchone()


# ---------- LOG CONFIG ----------

async def set_log_channel(guild_id: int, channel_id: int):
    db = get_db()
    await db.execute(
        """INSERT INTO log_config (guild_id, log_channel_id) VALUES (?, ?)
           ON CONFLICT(guild_id) DO UPDATE SET log_channel_id=excluded.log_channel_id""",
        (guild_id, channel_id),
    )
    await db.commit()


async def get_log_channel(guild_id: int):
    db = get_db()
    cur = await db.execute("SELECT log_channel_id FROM log_config WHERE guild_id=?", (guild_id,))
    row = await cur.fetchone()
    return row[0] if row else None


# ---------- GUILD SETTINGS ----------

async def set_report_channel(guild_id: int, channel_id: int):
    db = get_db()
    await db.execute(
        """INSERT INTO guild_settings (guild_id, report_channel_id) VALUES (?, ?)
           ON CONFLICT(guild_id) DO UPDATE SET report_channel_id=excluded.report_channel_id""",
        (guild_id, channel_id),
    )
    await db.commit()


async def get_report_channel(guild_id: int):
    db = get_db()
    cur = await db.execute("SELECT report_channel_id FROM guild_settings WHERE guild_id=?", (guild_id,))
    row = await cur.fetchone()
    return row[0] if row else None


async def set_report_forum(guild_id: int, forum_id: int):
    db = get_db()
    await db.execute(
        """INSERT INTO guild_settings (guild_id, report_forum_id) VALUES (?, ?)
           ON CONFLICT(guild_id) DO UPDATE SET report_forum_id=excluded.report_forum_id""",
        (guild_id, forum_id),
    )
    await db.commit()


async def get_report_forum(guild_id: int):
    db = get_db()
    cur = await db.execute("SELECT report_forum_id FROM guild_settings WHERE guild_id=?", (guild_id,))
    row = await cur.fetchone()
    return row[0] if row else None


async def set_language(guild_id: int, language: str):
    db = get_db()
    await db.execute(
        """INSERT INTO guild_settings (guild_id, language) VALUES (?, ?)
           ON CONFLICT(guild_id) DO UPDATE SET language=excluded.language""",
        (guild_id, language),
    )
    await db.commit()


async def get_language(guild_id: int) -> str:
    db = get_db()
    cur = await db.execute("SELECT language FROM guild_settings WHERE guild_id=?", (guild_id,))
    row = await cur.fetchone()
    return row[0] if row and row[0] else "ru"


async def set_warn_limit(guild_id: int, limit: int):
    db = get_db()
    await db.execute(
        """INSERT INTO guild_settings (guild_id, warn_limit) VALUES (?, ?)
           ON CONFLICT(guild_id) DO UPDATE SET warn_limit=excluded.warn_limit""",
        (guild_id, limit),
    )
    await db.commit()


async def get_warn_limit(guild_id: int) -> int:
    db = get_db()
    cur = await db.execute("SELECT warn_limit FROM guild_settings WHERE guild_id=?", (guild_id,))
    row = await cur.fetchone()
    return row[0] if row and row[0] else 0


async def set_antispam_enabled(guild_id: int, enabled: bool):
    db = get_db()
    await db.execute(
        """INSERT INTO guild_settings (guild_id, antispam_enabled) VALUES (?, ?)
           ON CONFLICT(guild_id) DO UPDATE SET antispam_enabled=excluded.antispam_enabled""",
        (guild_id, int(enabled)),
    )
    await db.commit()


async def get_antispam_enabled(guild_id: int) -> bool:
    db = get_db()
    cur = await db.execute("SELECT antispam_enabled FROM guild_settings WHERE guild_id=?", (guild_id,))
    row = await cur.fetchone()
    return bool(row[0]) if row else True


# ---------- ALLOWED DOMAINS ----------

async def add_allowed_domain(guild_id: int, domain: str):
    db = get_db()
    await db.execute(
        "INSERT OR IGNORE INTO allowed_domains (guild_id, domain) VALUES (?, ?)",
        (guild_id, domain.lower()),
    )
    await db.commit()


async def get_allowed_domains(guild_id: int) -> set[str]:
    db = get_db()
    cur = await db.execute("SELECT domain FROM allowed_domains WHERE guild_id=?", (guild_id,))
    rows = await cur.fetchall()
    return {r[0] for r in rows}
