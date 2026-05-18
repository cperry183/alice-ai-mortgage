# 🏠 MortgageAI — Intelligent Mortgage Broker Agent

An **agentic AI assistant** that guides borrowers through the complete mortgage application process via natural conversation, then automatically generates all required mortgage broker documents as professional PDFs.

[![CI/CD](https://github.com/your-username/mortgage-broker-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/mortgage-broker-agent/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

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
```

### Option 2: Local Development

```bash
# 1. Clone and enter directory
git clone https://github.com/your-username/mortgage-broker-agent.git
cd mortgage-broker-agent

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY

# 5. Run
make dev
# or: python main.py
```

---

## 🔑 Prerequisites

- **Anthropic API Key** — Get one at [console.anthropic.com](https://console.anthropic.com)
- **Docker & Docker Compose** (for containerized deployment)
  - Docker Desktop: [docs.docker.com/get-docker](https://docs.docker.com/get-docker/)
- **Python 3.12+** (for local development only)

---

## 🌐 App Pages & URLs

Docker Compose maps the Flask app from container port `5000` to host port `5001`.
Use `http://localhost:5001` when running with the included `docker-compose.yml`.

| Page | URL | Access | Description |
|------|-----|--------|-------------|
| Borrower application | `http://localhost:5001/` | Public | Main mortgage application chat. Borrowers start or continue an application here. |
| Login | `http://localhost:5001/login` | Public | Broker/admin login page. Protected pages redirect here when unauthenticated. |
| First admin setup | `http://localhost:5001/setup` | Public until first user exists | Creates the first administrator account. Once any user exists, this redirects to login. |
| Broker signup | `http://localhost:5001/signup` | Public if enabled | Lets new broker users create an account. Creates users with the `broker` role. |
| Broker dashboard | `http://localhost:5001/dashboard` | Logged-in users | Protected workspace for broker tools and compliance document assembly. |
| Billing | `http://localhost:5001/billing` | Logged-in users | Protected PayPal billing page. Shows PayPal subscription button when configured. |
| Agent metrics | `http://localhost:5001/admin/agent-metrics` | Admin only | Visual admin page for Anthropic agent runs, token usage, latency, and estimated cost. |
| Agent metrics API | `http://localhost:5001/api/admin/agent-metrics` | Admin only | Raw JSON metrics endpoint used by the visual metrics page. |
| Health check | `http://localhost:5001/api/health` | Public | Container/app health endpoint. |

### First-Time Admin Setup

1. Start the app with Docker.
2. Open `http://localhost:5001/setup`.
3. Create the first admin account.
4. Log in at `http://localhost:5001/login`.

The `/setup` page only works while the `users` table is empty. After the first user exists, use `/signup` for broker users or the admin user creation API.

### New User Signup

Open `http://localhost:5001/signup` to create a broker account. Public signup is enabled by default and can be disabled with:

```bash
ALLOW_PUBLIC_SIGNUP=false
```

When disabled, admins can still create users through the protected admin user API.

### Agent Metrics

Open `http://localhost:5001/admin/agent-metrics` after logging in as an admin.

The page shows:

- total agent runs
- successful and failed agent calls
- model name
- session id
- conversation stage
- input tokens
- output tokens
- total tokens
- latency
- estimated cost

Metrics are recorded when `/api/chat` calls the Anthropic Messages API. Older conversations are not backfilled; send a new chat message after deploying the metrics feature to see new rows.

Cost estimates use these configurable per-1M token rates:

```bash
ANTHROPIC_INPUT_COST_PER_1M=3.00
ANTHROPIC_OUTPUT_COST_PER_1M=15.00
```

### PayPal Billing

Open `http://localhost:5001/billing` after logging in.

For PayPal subscriptions, configure:

```bash
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_PLAN_ID=your_paypal_subscription_plan_id
PAYPAL_CURRENCY=USD
PAYPAL_MODE=sandbox
```

Optional fallback payment link:

```bash
PAYPAL_PAYMENT_LINK=https://www.paypal.com/...
```

If `PAYPAL_CLIENT_ID` and `PAYPAL_PLAN_ID` are set, the billing page renders PayPal subscription buttons. If only `PAYPAL_PAYMENT_LINK` is set, it displays a button that links to PayPal.

---

## 📁 Project Structure

```
mortgage-broker-agent/
├── app/
│   ├── agents/
│   │   ├── mortgage_agent.py        # Main AI agent (Claude integration)
│   │   └── conversation_state.py    # Session & state management
│   ├── documents/
│   │   └── document_generator.py    # PDF generation (all 6 documents)
│   ├── models/
│   │   ├── agent_metrics.py         # Agent usage/cost logging
│   │   ├── auth.py                  # User auth helpers
│   │   ├── crm.py                   # Borrower CRM operations
│   │   └── database.py              # SQLite schema/migrations
│   └── api/
│       └── server.py                # Flask REST API
├── templates/
│   ├── index.html                   # Borrower chat UI
│   ├── login.html                   # Login page
│   ├── signup.html                  # Broker signup page
│   ├── setup.html                   # First admin setup page
│   ├── dashboard.html               # Protected broker dashboard
│   ├── billing.html                 # PayPal billing page
│   └── agent_metrics.html           # Admin metrics page
├── tests/
│   └── test_mortgage_agent.py       # Comprehensive test suite
├── nginx/
│   └── nginx.conf                   # Reverse proxy config
├── .github/
│   └── workflows/
│       └── ci.yml                   # GitHub Actions CI/CD
├── Dockerfile                       # Container definition
├── docker-compose.yml               # Multi-service orchestration
├── requirements.txt                 # Python dependencies
├── Makefile                         # Developer shortcuts
├── .env.example                     # Environment template
└── main.py                          # Application entry point
```

---

## 🤖 How the Agent Works

The AI agent uses a **multi-stage conversation flow**:

```
Stage 1: Personal Information
    ↓ (name, DOB, SSN, address, contact info)
Stage 2: State Jurisdiction
    ↓ (MA, NH, NY, or CT disclosure path)
Stage 3: Employment & Income
    ↓ (employer, job title, income sources)
Stage 4: Assets
    ↓ (bank accounts, retirement, investments)
Stage 5: Liabilities & Debts
    ↓ (loans, credit cards, monthly obligations)
Stage 6: Property Information
    ↓ (property address, type, purchase price)
Stage 7: Loan Preferences
    ↓ (loan type, term, fixed/adjustable)
    
📄 Document Generation (automatic)
```

The agent collects 2-3 related questions at a time, validates inputs conversationally, and when all data is collected, triggers automatic PDF generation for all 6 documents.

---

## 🛠️ API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /` | GET | Borrower application chat UI |
| `GET /login` | GET | Login page |
| `POST /login` | POST | Authenticate a broker/admin user |
| `GET /setup` | GET | First admin setup page |
| `POST /setup` | POST | Create first admin account |
| `GET /signup` | GET | Broker signup page |
| `POST /signup` | POST | Create broker account |
| `GET /dashboard` | GET | Protected broker dashboard |
| `GET /billing` | GET | Protected PayPal billing page |
| `GET /admin/agent-metrics` | GET | Admin-only agent metrics page |
| `POST /api/session/new` | POST | Create new application session |
| `POST /api/chat` | POST | Send message, receive AI response |
| `GET /api/session/{id}/status` | GET | Get session progress |
| `POST /api/session/{id}/reset` | POST | Reset session |
| `GET /api/documents/{filename}` | GET | Download generated PDF |
| `GET /api/admin/agent-metrics` | GET | Admin-only JSON metrics endpoint |
| `POST /api/admin/users` | POST | Admin-only user creation API |
| `GET /api/health` | GET | Health check |

### Chat Request Format

```json
POST /api/chat
{
    "session_id": "uuid-here",
    "message": "My name is John Smith"
}
```

### Chat Response Format

```json
{
    "message": "Great, John! Now I'll need...",
    "stage": "personal",
    "complete": false,
    "progress": 15,
    "documents": []
}
```

---

## 🧪 Testing

```bash
# Run all tests
make test

# With coverage report
make test-cov

# Specific test class
pytest tests/ -k "TestDocumentGenerator" -v
```

---

## 🐳 Docker Commands

```bash
make build    # Build image
make run      # Start (detached)
make stop     # Stop containers
make logs     # Tail logs
make shell    # Shell into container
make clean    # Remove everything
```

---

## ⚙️ Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | **Yes** | — | Anthropic API key |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-6` | Anthropic model used by the mortgage agent |
| `ANTHROPIC_INPUT_COST_PER_1M` | No | `3.00` | Estimated input-token cost per 1M tokens |
| `ANTHROPIC_OUTPUT_COST_PER_1M` | No | `15.00` | Estimated output-token cost per 1M tokens |
| `SECRET_KEY` | No | `change-me` | Flask session secret |
| `PORT` | No | `5000` | Server port |
| `DEBUG` | No | `false` | Enable debug mode |
| `DOCS_OUTPUT_PATH` | No | `./generated_documents` | Host path for PDFs |
| `ALLOW_PUBLIC_SIGNUP` | No | `true` | Enables/disables `/signup` |
| `PAYPAL_CLIENT_ID` | No | — | PayPal client id for subscription buttons |
| `PAYPAL_PLAN_ID` | No | — | PayPal subscription plan id |
| `PAYPAL_CURRENCY` | No | `USD` | PayPal billing currency |
| `PAYPAL_MODE` | No | `sandbox` | PayPal mode label shown in UI |
| `PAYPAL_PAYMENT_LINK` | No | — | Optional fallback PayPal payment link |

---

## 🔒 Security Notes

- **Never commit `.env`** — It's in `.gitignore` by default
- Generated documents contain **sensitive PII** — secure your `generated_documents/` directory
- In production, use a proper `SECRET_KEY`, enable HTTPS via nginx, and consider Redis for session storage
- The Dockerfile runs as a **non-root user** (`appuser`)
- Document filename validation prevents path traversal attacks

---

## 📈 Production Deployment

```bash
# With nginx reverse proxy
docker compose --profile production up -d

# Scale workers
docker compose up -d --scale mortgage-agent=3
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Run tests: `make test`
4. Lint: `make lint`
5. Submit a pull request

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

## ⚠️ Disclaimer

This software is for **demonstration and educational purposes**. It is not a licensed mortgage broker service. All generated documents are templates and must be reviewed by a licensed mortgage professional before use in actual transactions. Do not use real SSNs or sensitive financial data in non-production environments.
