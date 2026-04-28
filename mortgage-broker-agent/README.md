# 🏠 MortgageAI — Intelligent Mortgage Broker Agent

An **agentic AI assistant** that guides borrowers through the complete mortgage application process via natural conversation, then automatically generates all required mortgage broker documents as professional PDFs.

[![CI/CD](https://github.com/your-username/mortgage-broker-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/mortgage-broker-agent/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

- **Conversational AI Agent** — Powered by Claude (Anthropic), guides borrowers through all 6 stages of mortgage application
- **Automatic Document Generation** — Produces 6 complete, professional mortgage documents
- **Real-time Progress Tracking** — Visual sidebar showing application completion status
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

# 4. Open http://localhost:5000
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

## 📁 Project Structure

```
mortgage-broker-agent/
├── app/
│   ├── agents/
│   │   ├── mortgage_agent.py        # Main AI agent (Claude integration)
│   │   └── conversation_state.py    # Session & state management
│   ├── documents/
│   │   └── document_generator.py    # PDF generation (all 6 documents)
│   └── api/
│       └── server.py                # Flask REST API
├── templates/
│   └── index.html                   # Web UI (single-page chat interface)
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
Stage 2: Employment & Income
    ↓ (employer, job title, income sources)
Stage 3: Assets
    ↓ (bank accounts, retirement, investments)
Stage 4: Liabilities & Debts
    ↓ (loans, credit cards, monthly obligations)
Stage 5: Property Information
    ↓ (property address, type, purchase price)
Stage 6: Loan Preferences
    ↓ (loan type, term, fixed/adjustable)
    
📄 Document Generation (automatic)
```

The agent collects 2-3 related questions at a time, validates inputs conversationally, and when all data is collected, triggers automatic PDF generation for all 6 documents.

---

## 🛠️ API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /` | GET | Web UI |
| `POST /api/session/new` | POST | Create new application session |
| `POST /api/chat` | POST | Send message, receive AI response |
| `GET /api/session/{id}/status` | GET | Get session progress |
| `POST /api/session/{id}/reset` | POST | Reset session |
| `GET /api/documents/{filename}` | GET | Download generated PDF |
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
| `SECRET_KEY` | No | `change-me` | Flask session secret |
| `PORT` | No | `5000` | Server port |
| `DEBUG` | No | `false` | Enable debug mode |
| `DOCS_OUTPUT_PATH` | No | `./generated_documents` | Host path for PDFs |

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
