"""
Flask API Server for Mortgage Broker Agent
"""

import os
import json
from flask import Flask, request, jsonify, send_file, render_template, session
from flask_cors import CORS
from app.agents.mortgage_agent import MortgageAgent
from app.agents.conversation_state import ConversationState
import uuid

app = Flask(__name__,
    template_folder="../templates",
    static_folder="../app/static")
app.secret_key = os.environ.get("SECRET_KEY", "mortgage-broker-dev-key-change-in-prod")
CORS(app)

# In-memory session storage (use Redis in production)
sessions: dict = {}
agent = MortgageAgent()


def get_or_create_session(session_id: str) -> ConversationState:
    if session_id not in sessions:
        sessions[session_id] = ConversationState()
    return sessions[session_id]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/session/new", methods=["POST"])
def new_session():
    """Create a new conversation session"""
    session_id = str(uuid.uuid4())
    sessions[session_id] = ConversationState()
    return jsonify({"session_id": session_id, "status": "created"})


@app.route("/api/chat", methods=["POST"])
def chat():
    """Process a chat message"""
    data = request.json
    session_id = data.get("session_id")
    user_message = data.get("message", "").strip()

    if not session_id or not user_message:
        return jsonify({"error": "session_id and message are required"}), 400

    state = get_or_create_session(session_id)

    if state.is_complete:
        return jsonify({
            "message": "Your application is already complete. You can download your documents below.",
            "complete": True,
            "stage": "complete",
            "documents": [
                {"name": d["name"], "filename": d["filename"], "id": d["id"]}
                for d in (state.application_data.raw.get("_documents", []) if state.application_data else [])
            ]
        })

    result = agent.chat(state, user_message)

    # Store documents in session data
    if result.get("complete") and result.get("documents"):
        if state.application_data:
            state.application_data.raw["_documents"] = result["documents"]

    return jsonify({
        "message": result["message"],
        "stage": result["stage"],
        "complete": result["complete"],
        "progress": state.get_progress_percent(),
        "documents": [
            {"name": d["name"], "filename": d["filename"], "id": d["id"], "generated": d["generated"]}
            for d in result.get("documents", [])
        ] if result.get("complete") else []
    })


@app.route("/api/session/<session_id>/status", methods=["GET"])
def session_status(session_id: str):
    """Get session status"""
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404
    state = sessions[session_id]
    return jsonify(state.to_dict())


@app.route("/api/documents/<filename>", methods=["GET"])
def download_document(filename: str):
    """Download a generated document"""
    # Security: only allow alphanumeric, underscore, hyphen, dot
    import re
    if not re.match(r'^[\w\-\.]+\.pdf$', filename):
        return jsonify({"error": "Invalid filename"}), 400

    filepath = os.path.join("/app/generated_docs", filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "Document not found"}), 404

    return send_file(filepath, as_attachment=True, download_name=filename,
                     mimetype="application/pdf")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "mortgage-broker-agent"})


@app.route("/api/session/<session_id>/reset", methods=["POST"])
def reset_session(session_id: str):
    """Reset/clear a session"""
    if session_id in sessions:
        sessions[session_id] = ConversationState()
    return jsonify({"status": "reset", "session_id": session_id})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
