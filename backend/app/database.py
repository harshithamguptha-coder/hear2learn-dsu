"""Small, beginner-friendly SQLite access layer using the standard library."""

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

DB_PATH = Path(
    os.getenv("DATABASE_PATH", Path(__file__).parent.parent / "classroom.db")
)


def connect_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # FastAPI may execute different parts of one request on different worker
    # threads. This connection is still scoped to one request and is never
    # shared, so allowing that handoff is safe for this small SQLite app.
    connection = sqlite3.connect(DB_PATH, timeout=5, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def get_db() -> Iterator[sqlite3.Connection]:
    """Open one database connection for the duration of a FastAPI request."""
    connection = connect_db()
    try:
        yield connection
    finally:
        connection.close()


def init_db() -> None:
    """Create the database file and tables if they do not exist yet."""
    connection = connect_db()
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                status TEXT NOT NULL CHECK (status IN ('active', 'ended')),
                started_at TEXT NOT NULL,
                ended_at TEXT
            );

            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE INDEX IF NOT EXISTS idx_transcripts_session_id
            ON transcripts(session_id, id);

            CREATE TABLE IF NOT EXISTS lecture_notes (
                session_id TEXT PRIMARY KEY,
                status TEXT NOT NULL CHECK (status IN ('ready', 'too_short')),
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                main_topics TEXT NOT NULL,
                key_points TEXT NOT NULL,
                important_terms TEXT NOT NULL,
                message TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            """
        )
        connection.commit()
    finally:
        connection.close()
