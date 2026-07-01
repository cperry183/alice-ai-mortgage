"""
Flask API Server — Mortgage Broker Agent
Features: Auth (Flask-Login), CRM, S3 storage, email notifications,
          input validation, audit logging.
"""
import os
import json
import uuid
from functools import wraps

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
from app.models.redis_client import get_session, save_session

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
agent = MortgageAgent()

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


def _is_valid_session_id(session_id: str) -> bool:
    try:
        return str(uuid.UUID(str(session_id))) == str(session_id)
    except (TypeError, ValueError, AttributeError):
        return False


def _safe_json_loads(raw, default):
    if not raw:
        return default
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return default


def _load_state(session_id: str) -> ConversationState | None:
    """Load session state from memory, Redis, or the CRM row."""
    if session_id in sessions:
        return sessions[session_id]

    snapshot = get_session(session_id)
    if snapshot:
        state = ConversationState.from_snapshot(snapshot)
        sessions[session_id] = state
        return state

    borrower = get_borrower(session_id)
    if not borrower:
        return None

    snapshot = _safe_json_loads(borrower.get("conversation_json"), {})
    if snapshot:
        state = ConversationState.from_snapshot(snapshot)
    else:
        state = ConversationState(session_id)

    application_data = _safe_json_loads(borrower.get("application_json"), {})
    if application_data:
        state.application_data = ApplicationData(application_data)

    if borrower.get("stage"):
        state.current_stage = borrower["stage"]
    if borrower.get("state_jurisdiction"):
        state.state_jurisdiction = borrower["state_jurisdiction"]
    if borrower.get("loan_type"):
        state.loan_type = borrower["loan_type"]
    state.is_self_employed = bool(borrower.get("is_self_employed", 0))
    state.sync_context_properties()

    sessions[session_id] = state
    save_session(session_id, state.to_snapshot())
    return state


def _save_state(state: ConversationState, documents=None):
    state.sync_context_properties()
    snapshot = state.to_snapshot()
    save_session(state.session_id, snapshot)
    sessions[state.session_id] = state

    update_fields = {
        "stage": state.current_stage,
        "progress": state.get_progress_percent(),
        "status": "complete" if state.is_complete else "active",
        "conversation_json": json.dumps(snapshot),
        "application_json": json.dumps(state.application_data.raw if state.application_data else {}),
    }
    update_fields.update(_crm_fields(state))
    if documents is not None:
        update_fields["documents"] = json.dumps(documents)
    update_borrower(state.session_id, **update_fields)


def _last_assistant_message(state: ConversationState) -> str:
    for message in reversed(state.get_messages()):
        if message.get("role") == "assistant":
            return message.get("content", "")
    return ""


def _validation_context(state: ConversationState) -> str:
    """Use the specific last question, not the full assistant response."""
    last_message = _last_assistant_message(state)
    lines = [line.strip() for line in last_message.splitlines() if line.strip()]
    for line in reversed(lines):
        if "?" in line:
            return line
    return last_message


def _client_ip() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    return forwarded_for.split(",", 1)[0].strip() or request.remote_addr or ""


def _safe_next_url(default: str = "dashboard"):
    next_url = request.form.get("next") or request.args.get("next") or ""
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


def _document_belongs_to_session(filename: str, session_id: str) -> bool:
    if not _is_valid_session_id(session_id):
        return False
    borrower = get_borrower(session_id)
    if not borrower:
        return False
    documents = _safe_json_loads(borrower.get("documents"), [])
    return any(
        isinstance(doc, dict)
        and filename in {doc.get("filename"), doc.get("file_name")}
        for doc in documents
    )


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.route("/", methods=["GET"])
def index_page():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if current_user.is_authenticated:
        return redirect(_safe_next_url())

    error = None
    email = ""
    next_url = request.args.get("next", "")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.verify(email, password)

        if user:
            login_user(user, remember=True)
            log_audit(user.id, "login", ip=_client_ip())
            return redirect(_safe_next_url())

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
    from app.models.database import get_db

    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()

    if count > 0:
        return redirect(url_for("login_page"))

    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not all([name, email, password]):
            error = "All fields are required."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif create_user(email, password, name, role="admin"):
            send_welcome(name, email)
            return redirect(url_for("login_page"))
        else:
            error = "An account with that email already exists."

    return render_template("setup.html", error=error)


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
@login_required
def agent_metrics_page():
    if not current_user.can("agent_metrics:read"):
        return redirect(url_for("dashboard"))
    return render_template("agent_metrics.html")


@app.route("/api/session/new", methods=["POST"])
def new_session():
    data = request.get_json(silent=True) or {}
    session_id = str(uuid.uuid4())
    state = ConversationState(session_id)

    jurisdiction = str(data.get("state_jurisdiction", "MA")).upper().strip()
    if jurisdiction not in {"MA", "NH", "NY", "CT"}:
        jurisdiction = "MA"
    state.state_jurisdiction = jurisdiction
    state.application_data = ApplicationData({
        "state_jurisdiction": jurisdiction,
        "property": {"subject_property_state": jurisdiction},
    })
    state.sync_context_properties()

    create_borrower(session_id)
    _save_state(state, documents=[])
    send_new_application(session_id)

    return jsonify({
        "session_id": session_id,
        "stage": state.current_stage,
        "progress": state.get_progress_percent(),
    }), 201


@app.route("/api/session/<session_id>/status", methods=["GET"])
def session_status(session_id):
    if not _is_valid_session_id(session_id):
        return jsonify({"error": "Invalid session_id"}), 400

    state = _load_state(session_id)
    borrower = get_borrower(session_id)
    if not state or not borrower:
        return jsonify({"error": "Session not found"}), 404

    documents = _safe_json_loads(borrower.get("documents"), [])
    return jsonify({
        **state.to_dict(),
        "documents": documents,
        "messages": state.get_messages(),
        "application_data": state.application_data.raw if state.application_data else {},
        "stage": state.current_stage,
        "suggestions": [] if state.is_complete else agent._suggestions_for_stage(state.current_stage),
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    if not _is_valid_session_id(session_id):
        return jsonify({"error": "Invalid session_id"}), 400

    raw_message = data.get("message", "")
    message = sanitize_input(raw_message)

    state = _load_state(session_id)
    if not state:
        return jsonify({"error": "Session not found"}), 404

    is_valid, errors = validate_message(message, context=_validation_context(state))
    if not is_valid:
        return jsonify({"error": errors[0] if errors else "Invalid message"}), 400

    try:
        result = agent.process_message(message, state)
    except Exception as exc:
        return jsonify({"error": "Agent processing failed", "detail": str(exc)}), 500

    documents = result.get("documents", [])
    _save_state(state, documents=documents if documents else None)

    if result.get("complete"):
        borrower_name = state.application_data.borrower_name if state.application_data else "Applicant"
        send_application_complete(borrower_name, state.session_id)

    return jsonify(result)


@app.route("/api/documents/generate", methods=["POST"])
@permission_required("documents:generate")
def assemble_documents():
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
                continue

            with open(full_dest_path, "w", encoding="utf-8") as handle:
                handle.write(rendered_html)

            generated_files.append({
                "form_id": form["form_id"],
                "name": form["name"],
                "file_name": output_filename,
            })
        except Exception as exc:
            app.logger.warning("Template generation failed for %s: %s", template_filename, exc)

    update_borrower(borrower_id, documents=json.dumps(generated_files))
    return jsonify({
        "status": "complete",
        "borrower_id": borrower_id,
        "state_processed": state_jurisdiction,
        "compiled_count": len(generated_files),
        "documents": generated_files,
    })


@app.route("/api/documents/<path:filename>", methods=["GET"])
def download_document(filename):
    safe = secure_filename(os.path.basename(filename))
    if not safe:
        return jsonify({"error": "Invalid document name"}), 400

    path = safe_join(DOCS_LOCAL, safe)
    if not path or not os.path.exists(path):
        return jsonify({"error": "Document not found"}), 404

    if not current_user.is_authenticated:
        session_id = request.args.get("session_id") or request.headers.get("X-Session-ID", "")
        if not _document_belongs_to_session(safe, session_id):
            return jsonify({"error": "Authentication required"}), 401
    else:
        log_audit(current_user.id, "download_doc", target_id=safe, ip=_client_ip())

    return send_file(path, as_attachment=True, download_name=safe)


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
    borrower = get_borrower(session_id)
    return (jsonify(borrower) if borrower else jsonify({"error": "Not found"})), (200 if borrower else 404)


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
    data = request.get_json(silent=True) or {}
    update_borrower(session_id, notes=data.get("notes", ""))
    return jsonify({"success": True})


@app.route("/api/admin/users", methods=["POST"])
@permission_required("users:create")
def admin_create_user():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    name = data.get("name", "").strip()
    role = data.get("role", "broker")

    if not all([email, password, name]):
        return jsonify({"error": "email, password, and name are required"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    if role not in VALID_USER_ROLES:
        return jsonify({"error": f"role must be one of: {', '.join(sorted(VALID_USER_ROLES))}"}), 400

    if create_user(email, password, name, role):
        send_welcome(name, email)
        log_audit(current_user.id, "create_user", detail=email, ip=_client_ip())
        return jsonify({"success": True})
    return jsonify({"error": "Email already exists"}), 409


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "mortgage-broker-agent",
        "storage": storage_backend(),
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
