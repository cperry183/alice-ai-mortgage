"""
Flask API Server — Mortgage Broker Agent
Features: Auth (Flask-Login), CRM, S3 storage, email notifications,
          input validation, audit logging.
"""
import os
import json
import uuid

from flask import (
    Flask, request, jsonify, send_file,
    render_template, redirect, url_for, flash,
)
from flask_cors import CORS
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user,
)

from app.agents.mortgage_agent import MortgageAgent
from app.agents.conversation_state import ConversationState

from app.models.database import init_db
from app.models.auth     import User, create_user, log_audit
from app.models.storage  import upload_document, get_download_url, storage_backend
from app.models.crm      import (
    create_borrower, update_borrower, get_all_borrowers,
    get_borrower, delete_borrower, get_stats,
)

from app.utils.email_utils import (
    send_application_complete, send_new_application, send_welcome,
)
from app.utils.validation import validate_message, sanitize_input

# ─────────────────────────────────────────────────────────────
# App & extensions
# ─────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder="../../templates",
    static_folder="../../static",
)
app.secret_key = os.environ.get("SECRET_KEY", "CHANGE-ME-IN-PRODUCTION")
CORS(app, resources={r"/api/*": {"origins": "*"}})

login_manager = LoginManager(app)
login_manager.login_view        = "login_page"
login_manager.login_message     = "Please sign in to access the broker dashboard."
login_manager.login_message_category = "info"

# Initialise SQLite (creates tables if needed)
init_db()

# In-memory agent sessions
sessions: dict = {}

DOCS_LOCAL = os.environ.get("DOCS_OUTPUT_PATH", "/app/generated_docs")
os.makedirs(DOCS_LOCAL, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# Flask-Login user loader
# ─────────────────────────────────────────────────────────────
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def _crm_fields(state: ConversationState) -> dict:
    """Pull whatever contact info the agent has collected."""
    fields = {}
    for attr, col in [
        ("borrower_name", "name"), ("full_name", "name"), ("name", "name"),
        ("email",         "email"),
        ("phone",         "phone"), ("phone_number", "phone"),
    ]:
        val = getattr(state, attr, None)
        if val and col not in fields:
            fields[col] = str(val)
    return fields


def _client_ip() -> str:
    return request.headers.get("X-Forwarded-For", request.remote_addr)


# ─────────────────────────────────────────────────────────────
# Auth routes (login / logout / setup)
# ─────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    error = None
    email = ""

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user     = User.verify(email, password)

        if user:
            login_user(user, remember=True)
            log_audit(user.id, "login", ip=_client_ip())
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid email or password. Please try again."
            log_audit(None, "login_failed", detail=email, ip=_client_ip())

    return render_template("login.html", error=error, email=email)


@app.route("/logout")
@login_required
def logout():
    log_audit(current_user.id, "logout", ip=_client_ip())
    logout_user()
    return redirect(url_for("login_page"))


@app.route("/setup", methods=["GET", "POST"])
def setup():
    """
    One-time setup to create the first broker account.
    Disable this route in production once your account is created.
    """
    from app.models.database import get_db
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()

    if count > 0:
        return redirect(url_for("login_page"))

    error = None
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not all([name, email, password]):
            error = "All fields are required."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        else:
            if create_user(email, password, name, role="admin"):
                send_welcome(name, email)
                return redirect(url_for("login_page"))
            else:
                error = "An account with that email already exists."

    return render_template("setup.html", error=error)


# ─────────────────────────────────────────────────────────────
# Web UI — public
# ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ─────────────────────────────────────────────────────────────
# Web UI — broker (protected)
# ─────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# ─────────────────────────────────────────────────────────────
# Session API
# ─────────────────────────────────────────────────────────────

@app.route("/api/session/new", methods=["POST"])
def new_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "agent": MortgageAgent(),
        "state": ConversationState(),
        "last_question": "",
    }
    create_borrower(session_id)
    send_new_application(session_id)   # notify broker
    return jsonify({"session_id": session_id})


@app.route("/api/session/<session_id>/status", methods=["GET"])
def session_status(session_id):
    borrower = get_borrower(session_id)
    if not borrower:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({
        "session_id": session_id,
        "stage":      borrower["stage"],
        "progress":   borrower["progress"],
        "status":     borrower["status"],
        "complete":   borrower["status"] == "complete",
        "documents":  json.loads(borrower["documents"] or "[]"),
    })


@app.route("/api/session/<session_id>/reset", methods=["POST"])
def reset_session(session_id):
    sessions[session_id] = {
        "agent": MortgageAgent(),
        "state": ConversationState(),
        "last_question": "",
    }
    update_borrower(
        session_id, stage="personal", progress=0,
        status="active", documents="[]",
    )
    return jsonify({"success": True, "session_id": session_id})


# ─────────────────────────────────────────────────────────────
# Chat — core AI loop
# ─────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def chat():
    body       = request.get_json(silent=True) or {}
    session_id = body.get("session_id")
    message    = body.get("message", "").strip()

    if not session_id or not message:
        return jsonify({"error": "session_id and message are required"}), 400

    message = sanitize_input(message)

    # ── Input validation ──────────────────────────────────────
    last_question = ""
    if session_id in sessions:
        last_question = sessions[session_id].get("last_question", "")

    valid, errors = validate_message(message, context=last_question)
    if not valid:
        return jsonify({
            "message":          errors[0],
            "validation_error": True,
            "stage":            sessions.get(session_id, {}).get("stage", "personal"),
            "progress":         0,
            "complete":         False,
            "documents":        [],
        })
    # ─────────────────────────────────────────────────────────

    # Restore or recreate session
    if session_id not in sessions:
        borrower = get_borrower(session_id)
        if not borrower:
            return jsonify({"error": "Session not found. Please start a new session."}), 404
        sessions[session_id] = {
            "agent": MortgageAgent(),
            "state": ConversationState(),
            "last_question": "",
        }

    agent = sessions[session_id]["agent"]
    state = sessions[session_id]["state"]

    try:
        response = agent.process_message(message, state)
    except Exception as exc:
        app.logger.error(f"Agent error [{session_id}]: {exc}", exc_info=True)
        return jsonify({"error": "The AI agent encountered an error. Please try again."}), 500

    # Store last question for next-message validation
    sessions[session_id]["last_question"] = response.get("message", "")

    # ── Document storage ──────────────────────────────────────
    documents = response.get("documents", [])
    if response.get("complete") and documents:
        for doc in documents:
            if doc.get("generated") and doc.get("filename"):
                local = os.path.join(DOCS_LOCAL, doc["filename"])
                if os.path.exists(local):
                    upload_document(local, doc["filename"])
                    doc["download_url"] = get_download_url(doc["filename"])
    # ─────────────────────────────────────────────────────────

    # ── Sync CRM ──────────────────────────────────────────────
    update_kwargs = {
        "stage":    response.get("stage", "personal"),
        "progress": response.get("progress", 0),
        "status":   "complete" if response.get("complete") else "active",
    }
    update_kwargs.update(_crm_fields(state))

    if response.get("complete") and documents:
        update_kwargs["documents"] = json.dumps(documents)
        borrower = get_borrower(session_id)
        if borrower:
            send_application_complete(
                borrower.get("name", "Borrower"), session_id
            )
    update_borrower(session_id, **update_kwargs)
    # ─────────────────────────────────────────────────────────

    return jsonify({
        "message":   response.get("message", ""),
        "stage":     response.get("stage", "personal"),
        "complete":  response.get("complete", False),
        "progress":  response.get("progress", 0),
        "documents": documents,
    })


# ─────────────────────────────────────────────────────────────
# Document download
# ─────────────────────────────────────────────────────────────

@app.route("/api/documents/<path:filename>", methods=["GET"])
def download_document(filename):
    safe = os.path.basename(filename)
    path = os.path.join(DOCS_LOCAL, safe)

    if not os.path.exists(path):
        return jsonify({"error": "Document not found"}), 404

    if current_user.is_authenticated:
        log_audit(current_user.id, "download_doc", target_id=safe, ip=_client_ip())

    return send_file(path, as_attachment=True, download_name=safe)


# ─────────────────────────────────────────────────────────────
# CRM API (broker only)
# ─────────────────────────────────────────────────────────────

@app.route("/api/crm/borrowers", methods=["GET"])
@login_required
def crm_list():
    return jsonify(get_all_borrowers())


@app.route("/api/crm/stats", methods=["GET"])
@login_required
def crm_stats():
    return jsonify(get_stats())


@app.route("/api/crm/borrowers/<session_id>", methods=["GET"])
@login_required
def crm_get(session_id):
    b = get_borrower(session_id)
    return (jsonify(b) if b else jsonify({"error": "Not found"})), (200 if b else 404)


@app.route("/api/crm/borrowers/<session_id>", methods=["DELETE"])
@login_required
def crm_delete(session_id):
    delete_borrower(session_id)
    sessions.pop(session_id, None)
    log_audit(current_user.id, "delete_borrower", target_id=session_id, ip=_client_ip())
    return jsonify({"success": True})


@app.route("/api/crm/borrowers/<session_id>/notes", methods=["POST"])
@login_required
def crm_notes(session_id):
    body = request.get_json(silent=True) or {}
    update_borrower(session_id, notes=body.get("notes", ""))
    return jsonify({"success": True})


# ─────────────────────────────────────────────────────────────
# Broker account management (admin only)
# ─────────────────────────────────────────────────────────────

@app.route("/api/admin/users", methods=["POST"])
@login_required
def admin_create_user():
    if current_user.role != "admin":
        return jsonify({"error": "Forbidden"}), 403

    body     = request.get_json(silent=True) or {}
    email    = body.get("email", "").strip().lower()
    password = body.get("password", "")
    name     = body.get("name", "").strip()
    role     = body.get("role", "broker")

    if not all([email, password, name]):
        return jsonify({"error": "email, password, and name are required"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    success = create_user(email, password, name, role)
    if success:
        send_welcome(name, email)
        log_audit(current_user.id, "create_user", detail=email, ip=_client_ip())
        return jsonify({"success": True})
    return jsonify({"error": "Email already exists"}), 409


# ─────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status":  "ok",
        "service": "mortgage-broker-agent",
        "storage": storage_backend(),
    })


# ─────────────────────────────────────────────────────────────
# Dev entry point
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
