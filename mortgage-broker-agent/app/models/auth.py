"""
Authentication — Mortgage Broker Agent
Flask-Login + werkzeug password hashing. Brokers only.
"""
import uuid
import sqlite3
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.database import get_db


class User(UserMixin):
    def __init__(self, id, email, name, role="broker"):
        self.id    = id
        self.email = email
        self.name  = name
        self.role  = role

    @staticmethod
    def get(user_id: str):
        conn = get_db()
        row  = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        if row:
            return User(row["id"], row["email"], row["name"], row["role"])
        return None

    @staticmethod
    def verify(email: str, password: str):
        conn = get_db()
        row  = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if row and check_password_hash(row["password_hash"], password):
            return User(row["id"], row["email"], row["name"], row["role"])
        return None


def create_user(email: str, password: str, name: str, role: str = "broker") -> bool:
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, name, role) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), email, generate_password_hash(password), name, role),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def log_audit(user_id: str, action: str, target_id: str = None,
              detail: str = None, ip: str = None):
    conn = get_db()
    conn.execute(
        "INSERT INTO audit_log (user_id, action, target_id, detail, ip_address) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, action, target_id, detail, ip),
    )
    conn.commit()
    conn.close()
