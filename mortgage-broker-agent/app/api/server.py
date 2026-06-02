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
from app.agents.conversation_state import ConversationState, ApplicationData

from app.models.database import init_db
from app.models.auth     import User, create_user, log_audit
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


@app.route("/", methods=["GET"])
def index_page():
    return render_template("index.html")


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

    is_valid, errors = validate_message(message, context=_last_assistant_message(state))
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
