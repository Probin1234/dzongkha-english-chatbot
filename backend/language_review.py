
"""Human review of suspected Tibetan-style expressions."""

from __future__ import annotations

import re
import sqlite3

from backend.database import DB_PATH


# Review indicators, not proof that a sentence is Tibetan.
REVIEW_TERMS = {
    "ཁྱེད་རང": "Check the form of address",
    "ཡོད་རེད": "Check the verb ending",
    "ཡིན་པས": "Check the verb ending",
    "ཡོད་པས": "Check the verb ending",
    "བདེ་པོ་ཡིན": "Check the expression",
    "ཀུ་ཟུ་བཟང": "Check greeting spelling",
}


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_review():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS language_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                english TEXT NOT NULL,
                dzongkha TEXT NOT NULL,
                roman TEXT NOT NULL DEFAULT '',
                gloss TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def detect(dzongkha):
    """Return reasons for manual review."""
    reasons = []

    if not re.search(r"[\u0F00-\u0FFF]", dzongkha):
        reasons.append("No Dzongkha-script characters found")

    for term, explanation in REVIEW_TERMS.items():
        if term in dzongkha:
            reasons.append(
                f"{explanation}: {term}"
            )

    return reasons


def inspect_and_queue(english, result):
    """Queue suspicious responses without blocking the chat."""
    init_review()

    dzongkha = result.get("dzongkha", "")
    reasons = detect(dzongkha)

    if not reasons:
        return False

    with connect() as conn:
        existing = conn.execute(
            """
            SELECT id FROM language_reviews
            WHERE english = ?
              AND dzongkha = ?
              AND status = 'pending'
            """,
            (english, dzongkha),
        ).fetchone()

        if not existing:
            conn.execute(
                """
                INSERT INTO language_reviews
                (english, dzongkha, roman, gloss, reason)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    english,
                    dzongkha,
                    result.get("roman", ""),
                    result.get("gloss", ""),
                    "; ".join(reasons),
                ),
            )

    return True


def pending_reviews():
    init_review()

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM language_reviews
            WHERE status = 'pending'
            ORDER BY id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def approve_correction(
    review_id,
    dzongkha,
    roman,
    gloss,
):
    """Approve a reviewed response and save it for reuse."""
    init_review()

    if not dzongkha.strip():
        return "Corrected Dzongkha is required."

    if not roman.strip():
        return "Pronunciation is required."

    if re.search(r"[\u0F00-\u0FFF]", roman):
        return "Pronunciation must use English letters."

    with connect() as conn:
        review = conn.execute(
            """
            SELECT * FROM language_reviews
            WHERE id = ? AND status = 'pending'
            """,
            (review_id,),
        ).fetchone()

        if review is None:
            return "Review not found."

        english = " ".join(
            review["english"].strip().lower().split()
        )

        conn.execute(
            """
            INSERT INTO glossary
            (english, dzongkha, roman, gloss)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(english) DO UPDATE SET
                dzongkha = excluded.dzongkha,
                roman = excluded.roman,
                gloss = excluded.gloss
            """,
            (
                english,
                dzongkha.strip(),
                roman.strip(),
                gloss.strip() or review["gloss"] or english,
            ),
        )

        conn.execute(
            """
            UPDATE language_reviews
            SET status = 'approved'
            WHERE id = ?
            """,
            (review_id,),
        )

    return None


def dismiss_review(review_id):
    init_review()

    with connect() as conn:
        conn.execute(
            """
            UPDATE language_reviews
            SET status = 'dismissed'
            WHERE id = ?
            """,
            (review_id,),
        )