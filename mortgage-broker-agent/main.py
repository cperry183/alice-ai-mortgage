"""
Mortgage Broker AI Agent - Entry Point
"""

from app.api.server import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
