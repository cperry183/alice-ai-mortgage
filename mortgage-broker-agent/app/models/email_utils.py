"""
Email Notifications — Mortgage Broker Agent
Uses smtplib (stdlib) — no extra pip dependency.
Configure via env vars; silently logs when disabled.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText

SMTP_HOST    = os.environ.get("SMTP_HOST",    "")
SMTP_PORT    = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER    = os.environ.get("SMTP_USER",    "")
SMTP_PASS    = os.environ.get("SMTP_PASS",    "")
BROKER_EMAIL = os.environ.get("BROKER_EMAIL", "")
FROM_EMAIL   = os.environ.get("FROM_EMAIL",   SMTP_USER)
APP_URL      = os.environ.get("APP_URL",      "http://localhost:5001")

ENABLED = all([SMTP_HOST, SMTP_USER, SMTP_PASS, BROKER_EMAIL])

# ── shared header / footer ────────────────────────────────────
_HEADER = """
<div style="font-family:'DM Sans',sans-serif;max-width:600px;margin:0 auto;">
  <div style="background:#0d1f35;padding:24px 28px;border-radius:12px 12px 0 0;
              display:flex;align-items:center;gap:12px;">
    <span style="font-size:28px;">🏠</span>
    <span style="font-family:Georgia,serif;font-size:1.3rem;color:white;font-weight:700;">
      Mortgage<span style="color:#f0d080;">AI</span>
    </span>
  </div>
  <div style="background:white;padding:28px;border:1px solid #e2e8f0;
              border-radius:0 0 12px 12px;">
"""
_FOOTER = """
    <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0;">
    <p style="color:#94a3b8;font-size:0.75rem;line-height:1.6;">
      This message was sent by MortgageAI. For licensed mortgage professionals only.<br>
      NMLS Consumer Access: <a href="https://www.nmlsconsumeraccess.org"
      style="color:#2563eb;">nmlsconsumeraccess.org</a>
    </p>
  </div>
</div>
"""

_BTN = (
    'display:inline-block;background:#2563eb;color:white;'
    'padding:12px 24px;border-radius:8px;text-decoration:none;'
    'font-weight:600;margin-top:16px;'
)


def _send(to: str, subject: str, html: str) -> bool:
    if not ENABLED:
        print(f"[email] DISABLED — would send '{subject}' to {to}")
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = FROM_EMAIL
    msg["To"]      = to
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as srv:
            srv.ehlo()
            srv.starttls()
            srv.login(SMTP_USER, SMTP_PASS)
            srv.sendmail(FROM_EMAIL, to, msg.as_string())
        return True
    except Exception as exc:
        print(f"[email] Send failed: {exc}")
        return False


# ── public helpers ────────────────────────────────────────────

def send_application_complete(borrower_name: str, session_id: str) -> bool:
    html = (
        _HEADER
        + f"""
        <h2 style="color:#0d1f35;margin-top:0;">✅ Application Complete</h2>
        <p style="color:#64748b;line-height:1.7;">
          <strong>{borrower_name}</strong> has completed their mortgage application.
          All 6 documents are generated and ready for your review.
        </p>
        <a href="{APP_URL}/dashboard" style="{_BTN}">View in Dashboard →</a>
        <p style="color:#94a3b8;font-size:0.78rem;margin-top:20px;">
          Session: {session_id}
        </p>
        """
        + _FOOTER
    )
    return _send(BROKER_EMAIL, f"✅ Application Complete — {borrower_name}", html)


def send_new_application(session_id: str) -> bool:
    html = (
        _HEADER
        + f"""
        <h2 style="color:#0d1f35;margin-top:0;">📋 New Application Started</h2>
        <p style="color:#64748b;line-height:1.7;">
          A borrower has started a new mortgage application and is being guided
          through the process now.
        </p>
        <a href="{APP_URL}/dashboard" style="{_BTN}">Monitor Progress →</a>
        <p style="color:#94a3b8;font-size:0.78rem;margin-top:20px;">
          Session: {session_id}
        </p>
        """
        + _FOOTER
    )
    return _send(BROKER_EMAIL, "📋 New Mortgage Application Started", html)


def send_welcome(broker_name: str, broker_email: str) -> bool:
    html = (
        _HEADER
        + f"""
        <h2 style="color:#0d1f35;margin-top:0;">Welcome, {broker_name}! 🎉</h2>
        <p style="color:#64748b;line-height:1.7;">
          Your MortgageAI broker account is ready. You can now manage borrower
          applications, download documents, and track progress from your dashboard.
        </p>
        <a href="{APP_URL}/dashboard" style="{_BTN}">Go to Dashboard →</a>
        """
        + _FOOTER
    )
    return _send(broker_email, "Welcome to MortgageAI", html)
