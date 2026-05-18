"""
SQLite Database — Mortgage Broker CRM
Tables: borrowers, users, audit_log
Updated for explicit Massachusetts (MA), New Hampshire (NH), New York (NY),
and Connecticut (CT) jurisdictional compliance.
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
            id                  TEXT PRIMARY KEY,
            name                TEXT DEFAULT 'New Applicant',
            email               TEXT DEFAULT '',
            phone               TEXT DEFAULT '',
            stage               TEXT DEFAULT 'personal',
            progress            INTEGER DEFAULT 0,
            status              TEXT DEFAULT 'active',
            
            -- State Jurisdiction Isolation Configuration
            state_jurisdiction  TEXT CHECK(state_jurisdiction IN ('MA', 'NH', 'NY', 'CT', NULL)),
            
            -- Dynamic Risk & Underwriting Profiles
            loan_type           TEXT DEFAULT 'CONVENTIONAL',
            is_self_employed    INTEGER DEFAULT 0 CHECK(is_self_employed IN (0, 1)),
            
            documents           TEXT DEFAULT '[]',
            notes               TEXT DEFAULT '',
            created_at          TEXT DEFAULT (datetime('now')),
            updated_at          TEXT DEFAULT (datetime('now'))
        );
    """)

    borrower_schema = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='borrowers'"
    ).fetchone()[0]
    if (
        "state_jurisdiction IN ('MA', 'NH', NULL)" in borrower_schema
        or "state_jurisdiction IN ('MA', 'NH', 'CT', NULL)" in borrower_schema
    ):
        conn.executescript("""
            DROP TRIGGER IF EXISTS trg_borrowers_updated_at;

            CREATE TABLE borrowers_new (
                id                  TEXT PRIMARY KEY,
                name                TEXT DEFAULT 'New Applicant',
                email               TEXT DEFAULT '',
                phone               TEXT DEFAULT '',
                stage               TEXT DEFAULT 'personal',
                progress            INTEGER DEFAULT 0,
                status              TEXT DEFAULT 'active',
                state_jurisdiction  TEXT CHECK(state_jurisdiction IN ('MA', 'NH', 'NY', 'CT', NULL)),
                loan_type           TEXT DEFAULT 'CONVENTIONAL',
                is_self_employed    INTEGER DEFAULT 0 CHECK(is_self_employed IN (0, 1)),
                documents           TEXT DEFAULT '[]',
                notes               TEXT DEFAULT '',
                created_at          TEXT DEFAULT (datetime('now')),
                updated_at          TEXT DEFAULT (datetime('now'))
            );

            INSERT INTO borrowers_new (
                id, name, email, phone, stage, progress, status,
                state_jurisdiction, loan_type, is_self_employed,
                documents, notes, created_at, updated_at
            )
            SELECT
                id, name, email, phone, stage, progress, status,
                state_jurisdiction, loan_type, is_self_employed,
                documents, notes, created_at, updated_at
            FROM borrowers;

            DROP TABLE borrowers;
            ALTER TABLE borrowers_new RENAME TO borrowers;
        """)

    conn.executescript("""

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

        -- Automated Compliance Trigger: Maintenance of modification timestamp
        CREATE TRIGGER IF NOT EXISTS trg_borrowers_updated_at
        AFTER UPDATE ON borrowers
        BEGIN
            UPDATE borrowers 
            SET updated_at = datetime('now') 
            WHERE id = NEW.id;
        END;
    """)
    conn.commit()
    conn.close()
