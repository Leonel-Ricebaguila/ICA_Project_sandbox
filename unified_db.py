#!/usr/bin/env python3
"""
Unified database utilities for ICA Project.
Combines user management (usuarios) and NFC card management (cards) into a single database.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.environ.get("ICA_DB_PATH", os.path.join(os.getcwd(), "ica_unified.db"))


@dataclass(frozen=True)
class UserRecord:
    id_usuario: int
    nombre: str
    correo: str
    rol: str
    ip_camara: Optional[str]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class CardRecord:
    uid: str
    id_usuario: Optional[int]  # Links to usuarios table
    role: int
    note: str
    created_at: str
    updated_at: str


def _ensure_directory(db_path: str) -> None:
    directory = os.path.dirname(db_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def initialize_database(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize the unified database with both usuarios and cards tables."""
    _ensure_directory(db_path)
    with sqlite3.connect(db_path) as conn:
        # Create usuarios table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                correo TEXT NOT NULL UNIQUE,
                rol TEXT NOT NULL,
                ip_camara TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
            """
        )
        
        # Create cards table with foreign key to usuarios
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cards (
                uid TEXT PRIMARY KEY,
                id_usuario INTEGER,
                role INTEGER NOT NULL,
                note TEXT DEFAULT '' NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario)
            )
            """
        )
        
        # Create triggers for updated_at
        conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_usuarios_updated
            AFTER UPDATE ON usuarios
            FOR EACH ROW BEGIN
                UPDATE usuarios SET updated_at = CURRENT_TIMESTAMP WHERE id_usuario = OLD.id_usuario;
            END;
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


# User management functions
def create_user(nombre: str, correo: str, rol: str, ip_camara: Optional[str] = None, 
                db_path: str = DEFAULT_DB_PATH) -> int:
    """Create a new user and return the user ID."""
    if not nombre or not correo or not rol:
        raise ValueError("nombre, correo, and rol are required")
    
    with _connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO usuarios (nombre, correo, rol, ip_camara) 
            VALUES (?, ?, ?, ?)
            """,
            (nombre, correo, rol, ip_camara)
        )
        return cur.lastrowid


def get_user_by_id(user_id: int, db_path: str = DEFAULT_DB_PATH) -> Optional[UserRecord]:
    """Get user by ID."""
    with _connect(db_path) as conn:
        cur = conn.execute(
            "SELECT id_usuario, nombre, correo, rol, ip_camara, created_at, updated_at FROM usuarios WHERE id_usuario = ?",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return UserRecord(*row)


def get_user_by_email(correo: str, db_path: str = DEFAULT_DB_PATH) -> Optional[UserRecord]:
    """Get user by email."""
    with _connect(db_path) as conn:
        cur = conn.execute(
            "SELECT id_usuario, nombre, correo, rol, ip_camara, created_at, updated_at FROM usuarios WHERE correo = ?",
            (correo,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return UserRecord(*row)


def list_users(db_path: str = DEFAULT_DB_PATH) -> List[UserRecord]:
    """List all users."""
    with _connect(db_path) as conn:
        cur = conn.execute(
            "SELECT id_usuario, nombre, correo, rol, ip_camara, created_at, updated_at FROM usuarios ORDER BY id_usuario ASC"
        )
        return [UserRecord(*row) for row in cur.fetchall()]


def update_user(user_id: int, nombre: Optional[str] = None, correo: Optional[str] = None, 
                rol: Optional[str] = None, ip_camara: Optional[str] = None, 
                db_path: str = DEFAULT_DB_PATH) -> bool:
    """Update user information."""
    updates = []
    params = []
    
    if nombre is not None:
        updates.append("nombre = ?")
        params.append(nombre)
    if correo is not None:
        updates.append("correo = ?")
        params.append(correo)
    if rol is not None:
        updates.append("rol = ?")
        params.append(rol)
    if ip_camara is not None:
        updates.append("ip_camara = ?")
        params.append(ip_camara)
    
    if not updates:
        return False
    
    params.append(user_id)
    
    with _connect(db_path) as conn:
        cur = conn.execute(
            f"UPDATE usuarios SET {', '.join(updates)} WHERE id_usuario = ?",
            params
        )
        return cur.rowcount > 0


def delete_user(user_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Delete a user and all associated cards."""
    with _connect(db_path) as conn:
        # Delete associated cards first
        conn.execute("DELETE FROM cards WHERE id_usuario = ?", (user_id,))
        # Delete user
        cur = conn.execute("DELETE FROM usuarios WHERE id_usuario = ?", (user_id,))
        return cur.rowcount > 0


# Card management functions
def upsert_card(uid: str, role: int, note: str = "", id_usuario: Optional[int] = None, 
                db_path: str = DEFAULT_DB_PATH) -> None:
    """Create or update a card."""
    if not uid:
        raise ValueError("UID must be a non-empty string")
    if not isinstance(role, int):
        raise ValueError("Role must be an integer")
    
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO cards (uid, id_usuario, role, note) VALUES (?, ?, ?, ?)
            ON CONFLICT(uid) DO UPDATE SET 
                id_usuario = excluded.id_usuario,
                role = excluded.role, 
                note = excluded.note
            """,
            (uid, id_usuario, role, note or "")
        )


def get_card(uid: str, db_path: str = DEFAULT_DB_PATH) -> Optional[CardRecord]:
    """Get card by UID."""
    with _connect(db_path) as conn:
        cur = conn.execute(
            "SELECT uid, id_usuario, role, note, created_at, updated_at FROM cards WHERE uid = ?", 
            (uid,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return CardRecord(*row)


def list_cards(db_path: str = DEFAULT_DB_PATH) -> List[CardRecord]:
    """List all cards."""
    with _connect(db_path) as conn:
        cur = conn.execute(
            "SELECT uid, id_usuario, role, note, created_at, updated_at FROM cards ORDER BY uid ASC"
        )
        return [CardRecord(*row) for row in cur.fetchall()]


def delete_card(uid: str, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Delete a card."""
    with _connect(db_path) as conn:
        cur = conn.execute("DELETE FROM cards WHERE uid = ?", (uid,))
        return cur.rowcount > 0


def get_cards_by_user(user_id: int, db_path: str = DEFAULT_DB_PATH) -> List[CardRecord]:
    """Get all cards for a specific user."""
    with _connect(db_path) as conn:
        cur = conn.execute(
            "SELECT uid, id_usuario, role, note, created_at, updated_at FROM cards WHERE id_usuario = ? ORDER BY uid ASC",
            (user_id,)
        )
        return [CardRecord(*row) for row in cur.fetchall()]


# Migration functions
def migrate_from_old_databases(old_usuarios_db: str, old_cards_db: str, 
                              new_db_path: str = DEFAULT_DB_PATH) -> None:
    """Migrate data from old separate databases to unified database."""
    logger.info("Starting migration from old databases...")
    
    # Initialize new database
    initialize_database(new_db_path)
    
    # Migrate usuarios
    with sqlite3.connect(old_usuarios_db) as old_conn:
        old_cur = old_conn.execute("SELECT id_usuario, nombre, correo, rol, ip_camara FROM usuarios")
        usuarios_data = old_cur.fetchall()
    
    with _connect(new_db_path) as new_conn:
        for row in usuarios_data:
            new_conn.execute(
                """
                INSERT OR IGNORE INTO usuarios (id_usuario, nombre, correo, rol, ip_camara)
                VALUES (?, ?, ?, ?, ?)
                """,
                row
            )
        logger.info(f"Migrated {len(usuarios_data)} users")
    
    # Migrate cards
    with sqlite3.connect(old_cards_db) as old_conn:
        old_cur = old_conn.execute("SELECT uid, role, note FROM cards")
        cards_data = old_cur.fetchall()
    
    with _connect(new_db_path) as new_conn:
        for row in cards_data:
            new_conn.execute(
                """
                INSERT OR IGNORE INTO cards (uid, role, note)
                VALUES (?, ?, ?)
                """,
                row
            )
        logger.info(f"Migrated {len(cards_data)} cards")
    
    logger.info("Migration completed successfully!")


if __name__ == "__main__":
    # Run migration
    migrate_from_old_databases("usuarios.db", "NFC_ServerSide/data.db")

