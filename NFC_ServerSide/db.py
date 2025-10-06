#!/usr/bin/env python3
"""
SQLite database utilities for storing NFC card UIDs and role levels.

This module provides a thin wrapper around sqlite3 for:
- creating the cards table on first use
- CRUD operations for records with columns: uid (TEXT PRIMARY KEY), role (INTEGER), note (TEXT)
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple


DEFAULT_DB_PATH = os.environ.get("NFC_DB_PATH", os.path.join(os.getcwd(), "data.db"))


@dataclass(frozen=True)
class CardRecord:
    uid: str
    role: int
    note: str


def _ensure_directory(db_path: str) -> None:
    directory = os.path.dirname(db_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def initialize_database(db_path: str = DEFAULT_DB_PATH) -> None:
    _ensure_directory(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cards (
                uid TEXT PRIMARY KEY,
                role INTEGER NOT NULL,
                note TEXT DEFAULT '' NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_cards_updated
            AFTER UPDATE ON cards
            FOR EACH ROW BEGIN
                UPDATE cards SET updated_at = CURRENT_TIMESTAMP WHERE uid = OLD.uid;
            END;
            """
        )


@contextmanager
def _connect(db_path: str = DEFAULT_DB_PATH):
    initialize_database(db_path)
    conn = sqlite3.connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_card(uid: str, role: int, note: str = "", db_path: str = DEFAULT_DB_PATH) -> None:
    if not uid:
        raise ValueError("UID must be a non-empty string")
    if not isinstance(role, int):
        raise ValueError("Role must be an integer")
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO cards (uid, role, note) VALUES (?, ?, ?)
            ON CONFLICT(uid) DO UPDATE SET role = excluded.role, note = excluded.note
            """,
            (uid, role, note or ""),
        )


def delete_card(uid: str, db_path: str = DEFAULT_DB_PATH) -> bool:
    with _connect(db_path) as conn:
        cur = conn.execute("DELETE FROM cards WHERE uid = ?", (uid,))
        return cur.rowcount > 0


def get_card(uid: str, db_path: str = DEFAULT_DB_PATH) -> Optional[CardRecord]:
    with _connect(db_path) as conn:
        cur = conn.execute("SELECT uid, role, note FROM cards WHERE uid = ?", (uid,))
        row = cur.fetchone()
        if not row:
            return None
        return CardRecord(uid=row[0], role=int(row[1]), note=row[2])


def list_cards(db_path: str = DEFAULT_DB_PATH) -> List[CardRecord]:
    with _connect(db_path) as conn:
        cur = conn.execute("SELECT uid, role, note FROM cards ORDER BY uid ASC")
        return [CardRecord(uid=r[0], role=int(r[1]), note=r[2]) for r in cur.fetchall()]


def exists(uid: str, db_path: str = DEFAULT_DB_PATH) -> bool:
    return get_card(uid, db_path=db_path) is not None


def bulk_import(records: Iterable[Tuple[str, int, str]], db_path: str = DEFAULT_DB_PATH) -> int:
    with _connect(db_path) as conn:
        cur = conn.executemany(
            """
            INSERT INTO cards (uid, role, note) VALUES (?, ?, ?)
            ON CONFLICT(uid) DO UPDATE SET role = excluded.role, note = excluded.note
            """,
            [(u, int(r), n or "") for (u, r, n) in records],
        )
        return cur.rowcount if cur.rowcount is not None else 0


