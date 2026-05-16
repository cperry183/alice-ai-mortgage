"""
Flask API Server — Mortgage Broker Agent (State-Isolated Topology)
Handles localized compliance tracking, automated audit trail logs,
CRM management, and rule-driven dynamic document assembly.
"""
import os
import json
import uuid

from flask import Flask, request, jsonify, send_file, render_template, redirect, url_for
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from app.agents.mortgage_agent import MortgageAgent
from app.agents.conversation_state import ConversationState

from app.models.database import init_db, get_db
from app.models.auth     import User, create_user, log_audit
from app.models.storage  import upload_document, get_download_url, storage_backend
from app.models.crm      import (
    create_borrower, update_borrower, get_all_borrowers,
    get_borrower, delete_borrower, get_stats,
)

from app.utils.email_utils import send_application_complete, send_new_application, send_welcome
from app.utils.validation import validate_message, sanitize_input
from app.utils.forms_manifest import generate_manifest

app = Flask(__name__, template_folder="../../templates", static_folder="../../static")
app.secret_key = os.environ.get("SECRET_KEY", "DE36A78BC923F46A122E1A8D4F7256AA")
CORS(app, resources={r"/api/*": {"origins": "*"}})

login_manager = LoginManager(app)
login_manager.login_view = "login_page"
login_manager.login_message = "Please sign in to access the broker dashboard."

init_db()
sessions: dict = {}
DOCS_LOCAL = os.environ.get("DOCS_OUTPUT_PATH", "/app/generated_docs")
os.makedirs(DOCS_LOCAL, exist_ok=True)


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


def _crm_fields(state: ConversationState) -> dict:
    fields = {}
    for attr, col in [
        ("borrower_name", "name"), ("full_name", "name"), ("name", "name"),
        ("email",         "email"),
        ("phone",         "phone"), ("phone_number", "phone"),
        ("state_jurisdiction", "state_jurisdiction")
    ]:
        val = getattr(state, attr, None)
        if val and col not in fields:
            fields[col] = str(val)
    return fields


def _client_ip() -> str:
    return request.headers.get("X-Forwarded-For", request.remote_addr)

# ─────────────────────────────────────────────────────────────
# State-Aware Broker Routing Core
# ─────────────────────────────────────────────────────────────

@app.route("/api/session/new", methods=["POST"])
def new_session():
    """
    Spawns a localized session context. 
    Requires explicit JSON payloads: {"state_jurisdiction": "MA"} or {"state_jurisdiction": "NH"}
    """
    body = request.get_json(silent=True) or {}
    state_param = body.get("state_jurisdiction", "").upper().strip()
    
    if state_param not in ["MA", "NH"]:
        return jsonify({"error": "Validation Fault: A valid state jurisdiction ('MA' or 'NH') must be targeted."}), 400

    session_id = str(uuid.uuid4())
    
    # Inject localized configurations immediately into runtime memory bounds
    initial_state = ConversationState()
    initial_state.state_jurisdiction = state_param

    sessions[session_id] = {
        "agent": MortgageAgent(),
        "state": initial_state,
        "last_question": "",
    }
    
    # Sync structural record directly out to database layout
    create_borrower(session_id)
    update_borrower(session_id, state_jurisdiction=state_param)
    
    send_new_application(session_id)   
    return jsonify({
        "session_id": session_id,
        "state_jurisdiction": state_param
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    body       = request.get_json(silent=True) or {}
    session_id = body.get("session_id")
    message    = body.get("message", "").strip()

    if not session_id or not message:
        return jsonify({"error": "session_id and message are required"}), 400

    message = sanitize_input(message)

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

    # Resiliency Fallback: Reconstruct tracking context from DB on a server recycle
    if session_id not in sessions:
        borrower = get_borrower(session_id)
        if not borrower:
            return jsonify({"error": "Session context timed out. Please clear cache and initialize."}), 404
        
        restored_state = ConversationState()
        restored_state.state_jurisdiction = borrower.get("state_jurisdiction", "MA")
        restored_state.borrower_name = borrower.get("name")
        restored_state.email = borrower.get("email")
        restored_state.phone = borrower.get("phone")
        
        sessions[session_id] = {
            "agent": MortgageAgent(),
            "state": restored_state,
            "last_question": "",
        }

    agent = sessions[session_id]["agent"]
    state = sessions[session_id]["state"]

    try:
        response = agent.process_message(message, state)
    except Exception as exc:
        app.logger.error(f"Agent Processing Engine Error [{session_id}]: {exc}", exc_info=True)
        return jsonify({"error": "Internal AI system processing fault. Re-attempt transaction."}), 500

    sessions[session_id]["last_question"] = response.get("message", "")

    # Intercept workflow completion to execute dynamic structural packaging
    is_complete = response.get("complete", False)
    if is_complete:
        # Resolve rules engine configurations against parameters tracked dynamically
        computed_manifest = generate_manifest(
            state_jurisdiction=state.state_jurisdiction,
            loan_type=getattr(state, "loan_type", "Conventional"),
            is_self_employed=getattr(state, "is_self_employed", False)
        )
        response["documents"] = computed_manifest

    documents = response.get("documents", [])
    if is_complete and documents:
        for doc in documents:
            if doc.get("generated") and doc.get("filename"):
                local = os.path.join(DOCS_LOCAL, doc["filename"])
                if os.path.exists(local):
                    upload_document(local, doc["filename"])
                    doc["download_url"] = get_download_url(doc["filename"])

    # Synchronize tracking metrics back into DB rows
    update_kwargs = {
        "stage":    response.get("stage", "personal"),
        "progress": response.get("progress", 0),
        "status":   "complete" if is_complete else "active",
    }
    update_kwargs.update(_crm_fields(state))

    if is_complete and documents:
        update_kwargs["documents"] = json.dumps(documents)
        borrower = get_borrower(session_id)
        if borrower:
            send_application_complete(borrower.get("name", "Borrower"), session_id)
            
    update_borrower(session_id, **update_kwargs)

    return jsonify({
        "message":            response.get("message", ""),
        "stage":              response.get("stage", "personal"),
        "complete":           is_complete,
        "progress":           response.get("progress", 0),
        "state_jurisdiction": state.state_jurisdiction,
        "documents":          documents,
    })

# ─────────────────────────────────────────────────────────────
# Retained Fallback Dashboard Handlers
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


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/session/<session_id>/status", methods=["GET"])
def session_status(session_id):
    borrower = get_borrower(session_id)
    if not borrower:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({
        "session_id":         session_id,
        "stage":              borrower["stage"],
        "progress":           borrower["progress"],
        "status":             borrower["status"],
        "state_jurisdiction": borrower.get("state_jurisdiction"),
        "complete":           borrower["status"] == "complete",
        "documents":          json.loads(borrower["documents"] or "[]"),
    })


@app.route("/api/crm/borrowers", methods=["GET"])
@login_required
def crm_list():
    return jsonify(get_all_borrowers())


if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)