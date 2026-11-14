"""Users, saved chats, and phrases an admin has taught."""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
from pathlib import Path

from backend.textbook import TEXTBOOK

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "druk.db"

ADMIN_EMAIL = "03230235@gmail.com"
ADMIN_PASSWORD = "admin101"
TEST_EMAIL = "test1@gmail.com"
TEST_PASSWORD = "test101"


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return salt, digest


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                english TEXT,
                dzongkha TEXT,
                roman TEXT,
                gloss TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS phrasebook (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                english TEXT,
                dzongkha TEXT NOT NULL,
                roman TEXT,
                gloss TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS glossary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                english TEXT NOT NULL UNIQUE,
                dzongkha TEXT NOT NULL,
                roman TEXT NOT NULL,
                gloss TEXT NOT NULL
            );
            """
        )
        _seed(conn, "Admin", ADMIN_EMAIL, ADMIN_PASSWORD, "admin")
        _seed(conn, "Test user", TEST_EMAIL, TEST_PASSWORD, "user")
        _seed_books(conn)


def _seed_books(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(phrasebook)")}
    if "kind" not in columns:
        conn.execute("ALTER TABLE phrasebook ADD COLUMN kind TEXT NOT NULL DEFAULT 'saved'")
    for user in conn.execute("SELECT id FROM users"):
        _give_book(conn, user["id"])


def _give_book(conn: sqlite3.Connection, user_id: int) -> None:
    for english, dzongkha, roman, gloss in TEXTBOOK:
        existing = conn.execute(
            "SELECT id FROM phrasebook WHERE user_id = ? AND kind = 'textbook' AND english = ?",
            (user_id, english),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE phrasebook SET dzongkha = ?, roman = ?, gloss = ? WHERE id = ?",
                (dzongkha, roman, gloss, existing["id"]),
            )
            continue
        conn.execute(
            """
            INSERT INTO phrasebook (user_id, english, dzongkha, roman, gloss, kind)
            VALUES (?, ?, ?, ?, ?, 'textbook')
            """,
            (user_id, english, dzongkha, roman, gloss),
        )


def _seed(conn: sqlite3.Connection, name: str, email: str, password: str, role: str) -> None:
    if conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
        return
    salt, digest = hash_password(password)
    conn.execute(
        "INSERT INTO users (name, email, salt, password_hash, role) VALUES (?, ?, ?, ?, ?)",
        (name, email, salt, digest, role),
    )


def authenticate(email: str, password: str):
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
    if row is None:
        return None
    _, digest = hash_password(password, row["salt"])
    if digest != row["password_hash"]:
        return None
    return row


def create_user(name: str, email: str, password: str) -> str | None:
    name = name.strip()
    email = email.strip().lower()
    if len(name) < 2:
        return "Enter your name."
    if "@" not in email or "." not in email.split("@")[-1]:
        return "Enter a real email."
    if len(password) < 6:
        return "Use at least 6 characters."
    with connect() as conn:
        if conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            return "That email is already registered."
        salt, digest = hash_password(password)
        conn.execute(
            "INSERT INTO users (name, email, salt, password_hash, role) VALUES (?, ?, ?, ?, 'user')",
            (name, email, salt, digest),
        )
        user_id = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()["id"]
        _give_book(conn, user_id)
    return None


def list_users():
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, name, email, role, created_at FROM users ORDER BY id"
        ).fetchall()
    return [dict(row) for row in rows]


def delete_user(user_id: int, actor_id: int) -> str | None:
    if user_id == actor_id:
        return "You cannot delete the account you are signed in with."
    with connect() as conn:
        row = conn.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            return "That account is already gone."
        if row["role"] == "admin":
            return "The admin account stays."
        chat_ids = [r["id"] for r in conn.execute("SELECT id FROM chats WHERE user_id = ?", (user_id,))]
        for chat_id in chat_ids:
            conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        conn.execute("DELETE FROM chats WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return None


def create_chat(user_id: int, title: str) -> int:
    with connect() as conn:
        cur = conn.execute("INSERT INTO chats (user_id, title) VALUES (?, ?)", (user_id, title[:80]))
        return int(cur.lastrowid)


def list_chats(user_id: int):
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, title FROM chats WHERE user_id = ? ORDER BY updated_at DESC, id DESC",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_chat(chat_id: int, user_id: int) -> None:
    with connect() as conn:
        owned = conn.execute(
            "SELECT id FROM chats WHERE id = ? AND user_id = ?",
            (chat_id, user_id),
        ).fetchone()
        if not owned:
            return
        conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))


def add_message(chat_id: int, role: str, **fields: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO messages (chat_id, role, english, dzongkha, roman, gloss)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                role,
                fields.get("english"),
                fields.get("dzongkha"),
                fields.get("roman"),
                fields.get("gloss"),
            ),
        )
        conn.execute("UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (chat_id,))


def get_messages(chat_id: int, user_id: int):
    with connect() as conn:
        owned = conn.execute(
            "SELECT id FROM chats WHERE id = ? AND user_id = ?",
            (chat_id, user_id),
        ).fetchone()
        if not owned:
            return []
        rows = conn.execute(
            "SELECT id, role, english, dzongkha, roman, gloss FROM messages WHERE chat_id = ? ORDER BY id",
            (chat_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def recent_replies(limit: int = 20):
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT m.created_at, u.email, m.english, m.dzongkha, m.roman
            FROM messages m
            JOIN chats c ON c.id = m.chat_id
            JOIN users u ON u.id = c.user_id
            WHERE m.role = 'assistant'
            ORDER BY m.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def stats() -> dict[str, int]:
    with connect() as conn:
        users = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        chats = conn.execute("SELECT COUNT(*) AS n FROM chats").fetchone()["n"]
        replies = conn.execute(
            "SELECT COUNT(*) AS n FROM messages WHERE role = 'assistant'"
        ).fetchone()["n"]
    return {"users": users, "chats": chats, "replies": replies}


def list_phrases(user_id: int):
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, english, dzongkha, roman, gloss, created_at, kind
            FROM phrasebook WHERE user_id = ? ORDER BY id
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def save_phrase(user_id: int, english: str, dzongkha: str, roman: str, gloss: str) -> bool:
    with connect() as conn:
        existing = conn.execute(
            "SELECT id FROM phrasebook WHERE user_id = ? AND dzongkha = ?",
            (user_id, dzongkha),
        ).fetchone()
        if existing:
            return False
        conn.execute(
            """
            INSERT INTO phrasebook (user_id, english, dzongkha, roman, gloss)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, english, dzongkha, roman, gloss),
        )
    return True


def delete_phrase(phrase_id: int, user_id: int) -> None:
    with connect() as conn:
        conn.execute(
            "DELETE FROM phrasebook WHERE id = ? AND user_id = ? AND kind != 'textbook'",
            (phrase_id, user_id),
        )


def glossary():
    with connect() as conn:
        rows = conn.execute(
            "SELECT english, dzongkha, roman, gloss FROM glossary ORDER BY english"
        ).fetchall()
    return [dict(row) for row in rows]


def add_glossary(english: str, dzongkha: str, roman: str, gloss: str) -> str | None:
    english = " ".join(english.strip().lower().split())
    if not english or not dzongkha.strip() or not roman.strip():
        return "English, Dzongkha, and pronunciation are required."
    try:
        with connect() as conn:
            conn.execute(
                "INSERT INTO glossary (english, dzongkha, roman, gloss) VALUES (?, ?, ?, ?)",
                (english, dzongkha.strip(), roman.strip(), gloss.strip() or english),
            )
    except sqlite3.IntegrityError:
        return "That English line is already saved."
    return None
