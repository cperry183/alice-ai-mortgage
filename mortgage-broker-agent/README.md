# MortgageAI — Intelligent Mortgage Broker Agent

An **agentic AI assistant** built as a security research lab for agentic AI in regulated workflows. The agent guides borrowers through the complete mortgage application process via natural conversation, then automatically generates all required mortgage broker documents as professional PDFs — while implementing Zero Trust controls for non-human identities.

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Lab Purpose:** This project is intentionally designed to study how to *secure* agentic AI that handles sensitive financial data — not for production use with real PII.

---

## ✨ Features

- **Conversational AI Agent** — Powered by Claude (Anthropic), guides borrowers through all 7 stages of mortgage application
- **Automatic Document Generation** — Produces 6 complete, professional mortgage documents
- **Real-time Progress Tracking** — Visual sidebar showing application completion status
- **Broker Authentication** — Admin setup, broker signup, login, and protected dashboard pages
- **Agent Metrics** — Admin-only tracking for Anthropic model usage, tokens, latency, and estimated cost
- **Billing Page** — Protected PayPal billing/subscription page with configurable PayPal settings
- **Instant PDF Downloads** — All documents available immediately upon completion
- **Fully Dockerized** — One-command deployment, no local dependencies needed
- **Production-Ready** — Gunicorn, nginx config, health checks, CI/CD pipeline included

---

## 🔒 Security Architecture (AI Security Lab Focus)

This project implements controls for **securing agentic AI as users**:

**1. Non-Human Identity (NHI)**
- Agent runs under scoped service identity, not user credentials
- Session-based authentication with Flask sessions
- Admin-only metrics endpoint (`/admin/agent-metrics`)

**2. Least Privilege**
- Document generation writes only to `./generated_documents/`
- Filename validation prevents path traversal
- Broker vs admin roles enforced on all protected routes

**3. Data Protection**
- Currently uses **synthetic test data only** — no real SSNs or financial data
- `.env` excluded via `.gitignore`
- PII fields marked for future encryption at rest

**4. AI-Specific Guardrails**
- Input sanitization on `/api/chat` to mitigate prompt injection (OWASP LLM01)
- Output filtering planned for sensitive data disclosure (OWASP LLM06)
- Token usage and cost tracking for anomaly detection
- All agent actions logged to SQLite for auditability

**Threat Model (OWASP LLM Top 10 mapping):**
- LLM01 Prompt Injection → Input validation on chat endpoint
- LLM02 Insecure Output Handling → PDF generation isolated from chat context
- LLM06 Sensitive Information Disclosure → Synthetic data only, future output filters
- LLM07 Insecure Plugin Design → Document generator runs as separate module with no network access
- LLM10 Model Theft → API key stored in environment, never logged

Aligned to **NIST AI RMF**: Govern (role-based access), Map (data flows documented), Measure (metrics logged), Manage (container isolation).

---

## 📄 Generated Documents

| Document | Description |
|----------|-------------|
| **Uniform Residential Loan Application (1003)** | Fannie Mae Form 1003 — the standard mortgage application |
| **Loan Estimate / Good Faith Estimate** | Itemized closing costs and payment projections |
| **Borrower Authorization Form** | Authorization to release information to third parties |
| **Privacy Notice (GLBA)** | Federal Gramm-Leach-Bliley Act privacy disclosure |
| **Credit Authorization** | Consent for hard credit pull |
| **Income & Asset Verification Summary** | Detailed income analysis, assets, DTI ratio, document checklist |

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/your-username/mortgage-broker-agent.git
cd mortgage-broker-agent

# 2. Set up environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Launch
make run
# or: docker compose up -d

# 4. Open http://localhost:5001

#### Local Development 
# 1. Clone and enter directory
git clone https://github.com/your-username/mortgage-broker-agent.git
cd mortgage-broker-agent

# 2. Create virtual environment
python -m venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY

# 5. Run
make dev
# or: python main.py
