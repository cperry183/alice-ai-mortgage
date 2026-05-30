# 🏠 MortgageAI — Intelligent Mortgage Broker Agent

An **agentic AI assistant** that guides borrowers through the full mortgage application lifecycle via natural conversation, then automatically generates a complete set of compliant mortgage documents as professional PDFs.

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

- Conversational Mortgage Agent — Powered by Anthropic Claude, guiding borrowers through a structured 7-stage workflow
- Automated Document Generation — Produces a full set of 6 mortgage-ready documents
- Progress Tracking UI — Real-time application progress visualization
- Broker Authentication System — Signup, login, role-based access control (admin/broker)
- Agent Observability — Token usage, latency, cost estimation, and session tracking
- Billing Integration — PayPal subscription + fallback payment link support
- Instant PDF Export — Documents generated and downloadable upon completion
- Dockerized Deployment — Fully containerized with one-command startup
- Production-Ready Stack — Gunicorn, nginx config, health checks, CI/CD pipeline included

---

## 📄 Generated Documents

| Document | Description |
|----------|-------------|
| Uniform Residential Loan Application (1003) | Standard Fannie Mae mortgage application |
| Loan Estimate / Good Faith Estimate | Itemized cost and payment breakdown |
| Borrower Authorization Form | Authorization for third-party data verification |
| GLBA Privacy Notice | Federal privacy disclosure requirement |
| Credit Authorization | Consent for credit pull |
| Income & Asset Verification Summary | Income analysis, assets, DTI, documentation checklist |

---

## 🚀 Quick Start

### 🐳 Docker (Recommended)

```bash
git clone https://github.com/your-username/mortgage-broker-agent.git
cd mortgage-broker-agent

cp .env.example .env
# Add your ANTHROPIC_API_KEY

make run
# or docker compose up -d

open http://localhost:5001
```

---

### 💻 Local Development

```bash
git clone https://github.com/your-username/mortgage-broker-agent.git
cd mortgage-broker-agent

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Configure ANTHROPIC_API_KEY

make dev
# or python main.py
```

---

## 🔑 Prerequisites

- Anthropic API Key → https://console.anthropic.com  
- Docker Desktop → https://docs.docker.com/get-docker/  
- Python 3.12+ (local development only)

---

## 🌐 Application Routes

| Page | URL | Access | Description |
|------|-----|--------|-------------|
| Borrower Chat | `/` | Public | Main mortgage application interface |
| Login | `/login` | Public | Broker/admin authentication |
| Setup | `/setup` | Public (first run only) | Initial admin creation |
| Signup | `/signup` | Configurable | Broker account creation |
| Dashboard | `/dashboard` | Authenticated | Broker workspace |
| Billing | `/billing` | Authenticated | PayPal subscription management |
| Agent Metrics | `/admin/agent-metrics` | Admin only | Observability dashboard |
| Health Check | `/api/health` | Public | Service health endpoint |

---

## 🧠 Agent Workflow

The mortgage agent follows a structured 7-stage intake process:

1. Personal Information  
2. Residency & Jurisdiction  
3. Employment & Income  
4. Assets  
5. Liabilities & Debts  
6. Property Details  
7. Loan Preferences  

Once complete, the system automatically triggers **document generation and PDF export**.

---

## 📡 API Overview

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Chat with mortgage agent |
| `/api/session/new` | POST | Create session |
| `/api/session/{id}/status` | GET | Session progress |
| `/api/documents/{file}` | GET | Download PDFs |
| `/api/health` | GET | Health check |

---

### Chat Request

```json
{
  "session_id": "uuid",
  "message": "My name is John Smith"
}
```

### Response

```json
{
  "message": "Thanks John, next I need...",
  "stage": "personal",
  "progress": 15,
  "complete": false
}
```

---

## 🧪 Testing

```bash
make test
make test-cov
pytest tests/ -k "TestDocumentGenerator" -v
```

---

## 🐳 Docker Commands

```bash
make build
make run
make stop
make logs
make shell
make clean
```

---

## ⚙️ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | required | Claude API key |
| `ANTHROPIC_MODEL` | claude-sonnet-4-6 | Model selection |
| `SECRET_KEY` | change-me | Flask session secret |
| `PORT` | 5000 | Server port |
| `DEBUG` | false | Debug mode |
| `DOCS_OUTPUT_PATH` | ./generated_documents | PDF output directory |
| `ALLOW_PUBLIC_SIGNUP` | true | Enable broker signup |
| `PAYPAL_CLIENT_ID` | — | PayPal integration |
| `PAYPAL_PLAN_ID` | — | Subscription plan |
| `PAYPAL_PAYMENT_LINK` | — | Fallback payment URL |

---

## 🔒 Security Design (OWASP LLM Top 10 Aligned)

This system is designed with a **zero-trust LLM architecture**, treating all model output as untrusted.

### Key Controls

**LLM01 — Prompt Injection Protection**  
Strict separation between system prompts, user input, and external data sources prevents instruction hijacking.

**LLM02 — Sensitive Data Exposure**  
System prompts, secrets, and runtime configuration are isolated from model context and output paths.

**LLM05 — Output Validation Layer**  
All LLM responses are sanitized and validated before being used in application logic or UI rendering.

**LLM06 — Controlled Agent Behavior**  
The model is restricted to advisory functions only. All state-changing operations are handled deterministically by backend logic.

**LLM10 — Abuse Protection**  
Rate limiting, token caps, and request throttling mitigate abuse and cost amplification risks.

### Security Posture

The system enforces a **zero-trust LLM execution model**, where the model is never allowed to directly execute actions. All outputs are treated as probabilistic suggestions and must pass validation layers before affecting system state.

---

## 📦 Project Structure

```
app/
  agents/
  documents/
  models/
  api/
templates/
tests/
nginx/
```

---

## 🚀 Production Deployment

```bash
docker compose --profile production up -d
docker compose up -d --scale mortgage-agent=3
```

---

## ⚠️ Compliance Notice

This software generates **draft mortgage documentation for informational and workflow automation purposes only**. All outputs must be reviewed by a **licensed mortgage professional** before use in real financial transactions. Do not input real SSNs or sensitive financial data in non-production environments.

