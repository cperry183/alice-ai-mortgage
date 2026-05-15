"""
SQLite Database — Mortgage Broker CRM
Tables: borrowers, users, audit_log
"""
import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "/app/data/mortgage.db")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS borrowers (
            id          TEXT PRIMARY KEY,
            name        TEXT DEFAULT 'New Applicant',
            email       TEXT DEFAULT '',
            phone       TEXT DEFAULT '',
            stage       TEXT DEFAULT 'personal',
            progress    INTEGER DEFAULT 0,
            status      TEXT DEFAULT 'active',
            documents   TEXT DEFAULT '[]',
            notes       TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS users (
            id            TEXT PRIMARY KEY,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name          TEXT NOT NULL,
            role          TEXT DEFAULT 'broker',
            created_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT,
            action      TEXT NOT NULL,
            target_id   TEXT,
            detail      TEXT,
            ip_address  TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()