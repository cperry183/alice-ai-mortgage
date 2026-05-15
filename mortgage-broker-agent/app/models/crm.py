"""
CRM Operations — Mortgage Broker Agent
"""
import json
from datetime import datetime
from app.models.database import get_db


def create_borrower(session_id: str):
    conn = get_db()
    conn.execute(
        'INSERT OR IGNORE INTO borrowers (id) VALUES (?)',
        (session_id,)
    )
    conn.commit()
    conn.close()


def update_borrower(session_id: str, **kwargs):
    if not kwargs:
        return
    kwargs['updated_at'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    set_clause = ', '.join(f'{k} = ?' for k in kwargs)
    values = list(kwargs.values()) + [session_id]
    conn = get_db()
    conn.execute(f'UPDATE borrowers SET {set_clause} WHERE id = ?', values)
    conn.commit()
    conn.close()


def get_all_borrowers():
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM borrowers ORDER BY updated_at DESC'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_borrower(session_id: str):
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM borrowers WHERE id = ?', (session_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_borrower(session_id: str):
    conn = get_db()
    conn.execute('DELETE FROM borrowers WHERE id = ?', (session_id,))
    conn.commit()
    conn.close()


def get_stats():
    conn = get_db()
    total    = conn.execute('SELECT COUNT(*) FROM borrowers').fetchone()[0]
    active   = conn.execute("SELECT COUNT(*) FROM borrowers WHERE status='active'").fetchone()[0]
    complete = conn.execute("SELECT COUNT(*) FROM borrowers WHERE status='complete'").fetchone()[0]
    week     = conn.execute(
        "SELECT COUNT(*) FROM borrowers WHERE created_at >= datetime('now','-7 days')"
    ).fetchone()[0]
    conn.close()
    return {'total': total, 'active': active, 'complete': complete, 'this_week': week}
