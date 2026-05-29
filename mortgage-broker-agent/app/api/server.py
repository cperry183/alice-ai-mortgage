"""
Flask API Server — Mortgage Broker Agent
Features: Auth (Flask-Login), CRM, S3 storage, email notifications,
          input validation, audit logging.
"""
import os
import json
import uuid
from functools import wraps
from urllib.parse import urlparse

from flask import (
    Flask, request, jsonify, send_file,
    render_template, redirect, url_for, flash,
)
from flask_cors import CORS
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user,
)
from werkzeug.security import safe_join
from werkzeug.utils import secure_filename

from app.agents.mortgage_agent import MortgageAgent
from app.agents.conversation_state import ConversationState, ApplicationData

from app.models.database import init_db
from app.models.auth     import User, VALID_USER_ROLES, create_user, log_audit
from app.models.storage  import upload_document, get_download_url, storage_backend
from app.models.crm      import (
    create_borrower, update_borrower, get_all_borrowers,
    get_borrower, delete_borrower, get_stats,
)
from app.models.agent_metrics import record_agent_run, get_agent_metrics

from app.utils.email_utils import (
    send_application_complete, send_new_application, send_welcome,
)
from app.utils.validation import validate_message, sanitize_input
from app.utils.forms_manifest import generate_manifest

# ─────────────────────────────────────────────────────────────
# App & extensions
# ─────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder="../../templates",
    static_folder="../../static",
)

DEFAULT_SECRET_KEY = "CHANGE-ME-IN-PRODUCTION"
WEAK_SECRET_KEYS = {
    "",
    DEFAULT_SECRET_KEY,
    "change-me",
    "changeme",
    "dev-only-change-me",
}


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _is_production() -> bool:
    return os.environ.get("FLASK_ENV", "").lower() == "production" or _env_flag("PRODUCTION")


def _secret_key() -> str:
    secret = os.environ.get("SECRET_KEY", "").strip()
    if _is_production() and secret in WEAK_SECRET_KEYS:
        raise RuntimeError("SECRET_KEY must be set to a strong value in production.")
    return secret or "dev-only-change-me"


def _allowed_cors_origins() -> list[str]:
    configured = os.environ.get("CORS_ALLOWED_ORIGINS", "").strip()
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    if _is_production():
        return []
    return [
        "http://localhost:3000",
        "http://localhost:5000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5000",
    ]


app.config.update(
    SECRET_KEY=_secret_key(),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE=os.environ.get("SESSION_COOKIE_SAMESITE", "Lax"),
    SESSION_COOKIE_SECURE=_env_flag("SESSION_COOKIE_SECURE", _is_production()),
    REMEMBER_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_SAMESITE=os.environ.get("REMEMBER_COOKIE_SAMESITE", "Lax"),
    REMEMBER_COOKIE_SECURE=_env_flag("REMEMBER_COOKIE_SECURE", _is_production()),
    MAX_CONTENT_LENGTH=int(os.environ.get("MAX_CONTENT_LENGTH", 1024 * 1024)),
)

cors_origins = _allowed_cors_origins()
if cors_origins:
    CORS(
        app,
        resources={r"/api/*": {"origins": cors_origins}},
        supports_credentials=True,
    )

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
    personal = state.application_data.personal if state.application_data else {}
    borrower_name = state.application_data.borrower_name if state.application_data else ""
    if borrower_name and borrower_name != "Applicant":
        fields["name"] = borrower_name
    if personal.get("email"):
        fields["email"] = str(personal["email"])
    if personal.get("phone") or personal.get("phone_number"):
        fields["phone"] = str(personal.get("phone") or personal.get("phone_number"))

    for attr, col in [
        ("borrower_name", "name"), ("full_name", "name"), ("name", "name"),
        ("email",         "email"),
        ("phone",         "phone"), ("phone_number", "phone"),
    ]:
        val = getattr(state, attr, None)
        if val and col not in fields:
            fields[col] = str(val)
    if state.state_jurisdiction:
        fields["state_jurisdiction"] = state.state_jurisdiction
    if state.loan_type:
        fields["loan_type"] = state.loan_type
    fields["is_self_employed"] = 1 if state.is_self_employed else 0
    return fields


def _state_from_borrower(session_id: str, borrower: dict) -> ConversationState:
    """Restore a conversation from persisted CRM fields and transcript."""
    snapshot = {}
    try:
        snapshot = json.loads(borrower.get("conversation_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        snapshot = {}

    state = ConversationState.from_snapshot(snapshot)
    state.session_id = session_id
    state.current_stage = borrower.get("stage") or state.current_stage
    state.state_jurisdiction = borrower.get("state_jurisdiction") or state.state_jurisdiction
    state.loan_type = borrower.get("loan_type") or state.loan_type
    state.is_self_employed = bool(borrower.get("is_self_employed"))

    if not state.application_data.raw:
        try:
            state.application_data = ApplicationData(json.loads(borrower.get("application_json") or "{}"))
        except (TypeError, json.JSONDecodeError):
            state.application_data = ApplicationData({})

    state.sync_context_properties()
    return state


def _persist_state(session_id: str, state: ConversationState, **kwargs):
    """Persist the live agent context so refreshes/restarts do not lose answers."""
    update_borrower(
        session_id,
        conversation_json=json.dumps(state.to_snapshot()),
        application_json=json.dumps(state.application_data.raw if state.application_data else {}),
        **kwargs,
    )


def _client_ip() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    return forwarded_for.split(",", 1)[0].strip() or request.remote_addr or ""


def _request_origin() -> str:
    origin = request.headers.get("Origin")
    if origin:
        return origin.rstrip("/")
    referer = request.headers.get("Referer")
    if referer:
        parsed = urlparse(referer)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    return ""


def _same_origin(origin: str) -> bool:
    if not origin:
        return True
    parsed = urlparse(origin)
    return parsed.scheme in {"http", "https"} and parsed.netloc == request.host


def _is_valid_session_id(session_id: str) -> bool:
    try:
        return str(uuid.UUID(str(session_id))) == str(session_id)
    except (TypeError, ValueError, AttributeError):
        return False


def _document_belongs_to_session(filename: str, session_id: str) -> bool:
    if not _is_valid_session_id(session_id):
        return False
    borrower = get_borrower(session_id)
    if not borrower:
        return False
    try:
        documents = json.loads(borrower.get("documents") or "[]")
    except (TypeError, json.JSONDecodeError):
        return False
    return any(
        isinstance(doc, dict)
        and filename in {doc.get("filename"), doc.get("file_name")}
        for doc in documents
    )


def _safe_next_url(default: str = "dashboard") -> str:
    next_url = request.form.get("next") or request.args.get("next") or ""
    if next_url == "/api/admin/agent-metrics":
        next_url = url_for("agent_metrics_page")
    if next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return url_for(default)


def permission_required(permission: str):
    def decorator(handler):
        @wraps(handler)
        @login_required
        def wrapper(*args, **kwargs):
            if not current_user.can(permission):
                return jsonify({"error": "Forbidden"}), 403
            return handler(*args, **kwargs)

        return wrapper

    return decorator


@app.before_request
def reject_cross_site_writes():
    if request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
        return None

    origin = _request_origin()
    if not origin:
        return None

    allowed_origins = {value.rstrip("/") for value in cors_origins}
    if not _same_origin(origin) and origin not in allowed_origins:
        return jsonify({"error": "Cross-site request rejected"}), 403
    return None


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=(), payment=()",
    )
    if request.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


def page_permission_required(permission: str, fallback: str = "dashboard"):
    def decorator(handler):
        @wraps(handler)
        @login_required
        def wrapper(*args, **kwargs):
            if not current_user.can(permission):
                return redirect(url_for(fallback))
            return handler(*args, **kwargs)

        return wrapper

    return decorator


# ─────────────────────────────────────────────────────────────
# Auth routes (login / logout / setup)
# ─────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if current_user.is_authenticated:
        return redirect(_safe_next_url())

    error = None
    email = ""
    next_url = request.args.get("next", "")
    if next_url == "/api/admin/agent-metrics":
        next_url = url_for("agent_metrics_page")

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user     = User.verify(email, password)

        if user:
            login_user(user, remember=True)
            log_audit(user.id, "login", ip=_client_ip())
            return redirect(_safe_next_url())
        else:
            error = "Invalid email or password. Please try again."
            log_audit(None, "login_failed", detail=email, ip=_client_ip())

    return render_template("login.html", error=error, email=email, next_url=next_url)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    signup_enabled = os.environ.get("ALLOW_PUBLIC_SIGNUP", "true").lower() in {"1", "true", "yes"}
    error = None
    name = ""
    email = ""

    if request.method == "POST":
        if not signup_enabled:
            error = "Public signup is currently disabled. Please contact an administrator."
        else:
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not all([name, email, password, confirm_password]):
                error = "All fields are required."
            elif len(password) < 8:
                error = "Password must be at least 8 characters."
            elif password != confirm_password:
                error = "Passwords do not match."
            elif create_user(email, password, name, role="broker"):
                user = User.verify(email, password)
                if user:
                    login_user(user, remember=True)
                    log_audit(user.id, "signup", ip=_client_ip())
                    send_welcome(name, email)
                    return redirect(url_for("dashboard"))
                return redirect(url_for("login_page"))
            else:
                error = "An account with that email already exists."

    return render_template(
        "signup.html",
        error=error,
        name=name,
        email=email,
        signup_enabled=signup_enabled,
    )


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


@app.route("/billing")
@login_required
def billing_page():
    paypal_config = {
        "client_id": os.environ.get("PAYPAL_CLIENT_ID", ""),
        "plan_id": os.environ.get("PAYPAL_PLAN_ID", ""),
        "currency": os.environ.get("PAYPAL_CURRENCY", "USD"),
        "payment_link": os.environ.get("PAYPAL_PAYMENT_LINK", ""),
        "mode": os.environ.get("PAYPAL_MODE", "sandbox"),
    }
    return render_template("billing.html", paypal=paypal_config)


@app.route("/admin/agent-metrics")
@page_permission_required("agent_metrics:read")
def agent_metrics_page():
    return render_template("agent_metrics.html")


@app.route("/api/documents/generate", methods=["POST"])
@permission_required("documents:generate")
def assemble_documents():
    """
    Compile localized compliance files from CRM state and available templates.
    """
    data = request.get_json(silent=True) or {}
    borrower_id = data.get("borrower_id")
    if not _is_valid_session_id(borrower_id):
        return jsonify({"error": "Invalid borrower_id"}), 400

    borrower = get_borrower(borrower_id)
    if not borrower:
        return jsonify({"error": f"Borrower record '{borrower_id}' not found"}), 404

    state_jurisdiction = (
        borrower.get("state_jurisdiction")
        or borrower.get("state")
        or "MA"
    ).upper().strip()
    loan_type = (borrower.get("loan_type") or "CONVENTIONAL").upper().strip()
    is_self_employed = bool(borrower.get("is_self_employed"))

    required_forms = generate_manifest(state_jurisdiction, loan_type, is_self_employed)
    generated_files = []

    for form in required_forms:
        form_id = form["form_id"].lower()
        template_filename = f"{form_id}.html"
        template_path = os.path.join(app.template_folder, template_filename)

        if not os.path.exists(template_path):
            continue

        try:
            rendered_html = render_template(template_filename, borrower=borrower)
            output_filename = f"{borrower_id}_{form_id}_{uuid.uuid4().hex[:6]}.html"
            full_dest_path = safe_join(DOCS_LOCAL, secure_filename(output_filename))
            if not full_dest_path:
                app.logger.warning("Unsafe generated document path rejected: %s", output_filename)
                continue

            with open(full_dest_path, "w", encoding="utf-8") as handle:
                handle.write(rendered_html)

            generated_files.append({
                "form_id": form["form_id"],
                "name": form["name"],
                "file_name": output_filename,
            })
        except Exception as exc:
            app.logger.warning(
                "Template generation failed for %s [%s]: %s",
                template_filename,
                borrower_id,
                exc,
            )

    return jsonify({
        "status": "complete",
        "borrower_id": borrower_id,
        "state_processed": state_jurisdiction,
        "compiled_count": len(generated_files),
        "documents": generated_files,
    })


# ─────────────────────────────────────────────────────────────
# Session API
# ─────────────────────────────────────────────────────────────

@app.route("/api/session/new", methods=["POST"])
def new_session():
    body = request.get_json(silent=True) or {}
    state_jurisdiction = str(body.get("state_jurisdiction") or "MA").upper().strip()
    if state_jurisdiction not in {"MA", "NH", "NY", "CT"}:
        state_jurisdiction = "MA"

    session_id = str(uuid.uuid4())
    state = ConversationState()
    state.session_id = session_id
    state.state_jurisdiction = state_jurisdiction
    sessions[session_id] = {
        "agent": MortgageAgent(),
        "state": state,
        "last_question": "",
    }
    create_borrower(session_id)
    _persist_state(session_id, state, state_jurisdiction=state_jurisdiction)
    send_new_application(session_id)   # notify broker
    return jsonify({"session_id": session_id})


@app.route("/api/session/<session_id>/status", methods=["GET"])
def session_status(session_id):
    if not _is_valid_session_id(session_id):
        return jsonify({"error": "Invalid session_id"}), 400

    borrower = get_borrower(session_id)
    if not borrower:
        return jsonify({"error": "Session not found"}), 404
    messages = []
    try:
        snapshot = json.loads(borrower.get("conversation_json") or "{}")
        messages = snapshot.get("messages") or []
    except (TypeError, json.JSONDecodeError):
        messages = []
    return jsonify({
        "session_id": session_id,
        "stage":      borrower["stage"],
        "progress":   borrower["progress"],
        "status":     borrower["status"],
        "complete":   borrower["status"] == "complete",
        "documents":  json.loads(borrower["documents"] or "[]"),
        "messages":   [
            {"role": m.get("role"), "content": m.get("content")}
            for m in messages
            if isinstance(m, dict) and m.get("role") in {"user", "assistant"} and m.get("content")
        ],
    })


@app.route("/api/session/<session_id>/reset", methods=["POST"])
def reset_session(session_id):
    if not _is_valid_session_id(session_id):
        return jsonify({"error": "Invalid session_id"}), 400

    if not get_borrower(session_id):
        return jsonify({"error": "Session not found"}), 404

    state = ConversationState()
    state.session_id = session_id
    sessions[session_id] = {
        "agent": MortgageAgent(),
        "state": state,
        "last_question": "",
    }
    _persist_state(
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
    if not _is_valid_session_id(session_id):
        return jsonify({"error": "Invalid session_id"}), 400

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
            "state": _state_from_borrower(session_id, borrower),
            "last_question": "",
        }

    agent = sessions[session_id]["agent"]
    state = sessions[session_id]["state"]

    try:
        response = agent.process_message(message, state)
    except Exception as exc:
        record_agent_run(
            session_id=session_id,
            model=getattr(agent, "model", "unknown"),
            status="error",
            stage=getattr(state, "current_stage", ""),
            error=str(exc),
        )
        app.logger.error(f"Agent error [{session_id}]: {exc}", exc_info=True)
        return jsonify({"error": "The AI agent encountered an error. Please try again."}), 500

    metrics = response.get("agent_metrics") or {}
    record_agent_run(
        session_id=session_id,
        model=metrics.get("model") or getattr(agent, "model", "unknown"),
        status="success",
        stage=response.get("stage", getattr(state, "current_stage", "")),
        input_tokens=metrics.get("input_tokens", 0),
        output_tokens=metrics.get("output_tokens", 0),
        latency_ms=metrics.get("latency_ms", 0),
    )

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
    _persist_state(session_id, state, **update_kwargs)
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
    safe = secure_filename(os.path.basename(filename))
    if not safe:
        return jsonify({"error": "Invalid document name"}), 400

    path = safe_join(DOCS_LOCAL, safe)
    if not path:
        return jsonify({"error": "Invalid document name"}), 400

    if not os.path.exists(path):
        return jsonify({"error": "Document not found"}), 404

    if current_user.is_authenticated:
        log_audit(current_user.id, "download_doc", target_id=safe, ip=_client_ip())
    else:
        session_id = request.args.get("session_id") or request.headers.get("X-Session-ID", "")
        if not _document_belongs_to_session(safe, session_id):
            return jsonify({"error": "Authentication required"}), 401

    return send_file(path, as_attachment=True, download_name=safe)


# ─────────────────────────────────────────────────────────────
# CRM API (broker only)
# ─────────────────────────────────────────────────────────────

@app.route("/api/crm/borrowers", methods=["GET"])
@permission_required("borrowers:read")
def crm_list():
    return jsonify(get_all_borrowers())


@app.route("/api/crm/stats", methods=["GET"])
@permission_required("borrowers:read")
def crm_stats():
    return jsonify(get_stats())


@app.route("/api/crm/borrowers/<session_id>", methods=["GET"])
@permission_required("borrowers:read")
def crm_get(session_id):
    b = get_borrower(session_id)
    return (jsonify(b) if b else jsonify({"error": "Not found"})), (200 if b else 404)


@app.route("/api/crm/borrowers/<session_id>", methods=["DELETE"])
@permission_required("borrowers:delete")
def crm_delete(session_id):
    delete_borrower(session_id)
    sessions.pop(session_id, None)
    log_audit(current_user.id, "delete_borrower", target_id=session_id, ip=_client_ip())
    return jsonify({"success": True})


@app.route("/api/crm/borrowers/<session_id>/notes", methods=["POST"])
@permission_required("borrowers:update")
def crm_notes(session_id):
    body = request.get_json(silent=True) or {}
    update_borrower(session_id, notes=body.get("notes", ""))
    return jsonify({"success": True})


# ─────────────────────────────────────────────────────────────
# Broker account management (admin only)
# ─────────────────────────────────────────────────────────────

@app.route("/api/admin/users", methods=["POST"])
@permission_required("users:create")
def admin_create_user():
    body     = request.get_json(silent=True) or {}
    email    = body.get("email", "").strip().lower()
    password = body.get("password", "")
    name     = body.get("name", "").strip()
    role     = body.get("role", "broker")

    if not all([email, password, name]):
        return jsonify({"error": "email, password, and name are required"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    if role not in VALID_USER_ROLES:
        return jsonify({"error": f"role must be one of: {', '.join(sorted(VALID_USER_ROLES))}"}), 400

    success = create_user(email, password, name, role)
    if success:
        send_welcome(name, email)
        log_audit(current_user.id, "create_user", detail=email, ip=_client_ip())
        return jsonify({"success": True})
    return jsonify({"error": "Email already exists"}), 409


@app.route("/api/admin/agent-metrics", methods=["GET"])
@permission_required("agent_metrics:read")
def admin_agent_metrics():
    try:
        limit = int(request.args.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    return jsonify(get_agent_metrics(limit=max(1, min(limit, 200))))


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
