"""
Flask API Server — Mortgage Broker Agent (State-Isolated Topology)
Handles localized compliance tracking, automated audit trail logs,
CRM management, and rule-driven dynamic document assembly.
"""

import os
import json
import uuid

from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from app.agents.mortgage_agent import MortgageAgent
from app.agents.conversation_state import ConversationState

from app.models.database import init_db, get_db
from app.models.auth     import User, create_user, log_audit
from app.models.storage  import upload_document, get_download_url
from app.models.crm      import (
    create_borrower, update_borrower, get_all_borrowers,
    get_borrower
)

from app.utils.email_utils import send_application_complete, send_new_application
from app.utils.validation import validate_message, sanitize_input
from app.utils.forms_manifest import generate_manifest

# Global state tracking
sessions: dict = {}
DOCS_LOCAL = os.environ.get("DOCS_OUTPUT_PATH", "/app/generated_docs")
os.makedirs(DOCS_LOCAL, exist_ok=True)

# ─────────────────────────────────────────────────────────────
#  Global Core App Initialization & Configuration
# ─────────────────────────────────────────────────────────────

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "DE36A78BC923F46A122E1A8D4F7256AA")

CORS(app, resources={r"/api/*": {"origins": "*"}})

login_manager = LoginManager()
login_manager.login_view = "login_page"
login_manager.login_message = "Please sign in to access the broker dashboard."
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

with app.app_context():
    init_db()

# ─────────────────────────────────────────────────────────────
#  Core Authentication View Endpoints
# ─────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login_page():
    error = None
    email = ""
    
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        
        user = User.verify(email, password)
        
        if user:
            login_user(user)
            db = get_db()
            log_audit(db, user.id, "LOGIN_SUCCESS", "User authenticated successfully")
            return redirect(url_for("dashboard_page"))
        else:
            error = "Invalid email credentials or master authorization token entry."
            
    return render_template("login.html", error=error, email=email)

@app.route("/logout")
@login_required
def logout_action():
    db = get_db()
    log_audit(db, current_user.id, "LOGOUT", "User closed active dashboard session")
    logout_user()
    return redirect(url_for("login_page"))

# ─────────────────────────────────────────────────────────────
#  Dashboard & Dynamic Document Assembly Engine
# ─────────────────────────────────────────────────────────────

@app.route("/")
@app.route("/dashboard")
@login_required
def dashboard_page():
    return "<h1>Mortgage Broker Dashboard - Session Validated</h1>"

@app.route("/api/documents/generate", methods=["POST"])
@login_required
def assemble_documents():
    """
    Compiles localized compliance files dynamically by tying CRM data 
    structures to the state rules engine matrix (MA, NH, NY, CT).
    """
    data = request.json or {}
    borrower_id = data.get("borrower_id")
    
    # 1. Fetch data directly out of your established CRM storage engine
    borrower = get_borrower(borrower_id)
    if not borrower:
        return jsonify({"error": f"Borrower record '{borrower_id}' not found"}), 404
        
    # 2. Extract state context and employment classifications
    state_jurisdiction = (
        borrower.get("state_jurisdiction")
        or borrower.get("state")
        or "MA"
    ).upper().strip()
    loan_type = borrower.get("loan_type", "CONVENTIONAL").upper().strip()
    is_self_employed = borrower.get("employment_status", "").upper() == "SELF_EMPLOYED"
    
    # 3. Compile structural list using your newly updated manifest file parameters
    required_forms = generate_manifest(state_jurisdiction, loan_type, is_self_employed)
    
    generated_files = []
    
    # 4. Cycle through and cleanly map available templates into your persistent storage path
    for form in required_forms:
        form_id = form["form_id"].lower()
        template_filename = f"{form_id}.html"
        
        # Guard statement checking if a template has been written for this specific layout yet
        template_path = os.path.join(app.template_folder, template_filename)
        if not os.path.exists(template_path):
            continue
            
        try:
            rendered_html = render_template(template_filename, borrower=borrower)
            
            # Save using your isolated UUID naming layout inside your mount folder
            output_filename = f"{borrower_id}_{form_id}_{uuid.uuid4().hex[:6]}.html"
            full_dest_path = os.path.join(DOCS_LOCAL, output_filename)
            
            with open(full_dest_path, "w") as f:
                f.write(rendered_html)
                
            generated_files.append({
                "form_id": form["form_id"],
                "name": form["name"],
                "file_name": output_filename
            })
        except Exception as e:
            # Prevent single template runtime failures from dropping the whole generation thread
            continue
            
    return jsonify({
        "status": "complete",
        "borrower_id": borrower_id,
        "state_processed": state_jurisdiction,
        "compiled_count": len(generated_files),
        "documents": generated_files
    }), 200

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "mortgage-broker-agent",
        "port_context": os.environ.get("PORT", "5001")
    }), 200

# ─────────────────────────────────────────────────────────────
#  Local Native Application Server Execution Context
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    
    print(f"[*] Starting local native Python runtime execution thread on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=debug)
