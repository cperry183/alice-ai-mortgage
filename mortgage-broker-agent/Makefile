# ─────────────────────────────────────────────────────────────
#  Mortgage Broker Agent — Makefile
# ─────────────────────────────────────────────────────────────

.PHONY: help build run stop dev test lint clean docs

# Default target
help:
	@echo ""
	@echo "  Mortgage Broker Agent — Available Commands"
	@echo "  ─────────────────────────────────────────"
	@echo "  make build    Build the Docker image"
	@echo "  make run      Start the application (Docker)"
	@echo "  make stop     Stop all containers"
	@echo "  make dev      Run in development mode (local Python)"
	@echo "  make test     Run the test suite"
	@echo "  make lint     Run linting and formatting checks"
	@echo "  make clean    Remove containers and generated files"
	@echo "  make logs     Tail container logs"
	@echo "  make shell    Open shell in running container"
	@echo ""

# Build Docker image
build:
	@echo "🔨 Building Docker image..."
	docker compose build

# Start with Docker Compose
run:
	@echo "🚀 Starting Mortgage Broker Agent..."
	@test -f .env || (cp .env.example .env && echo "⚠️  Created .env from template — please add your ANTHROPIC_API_KEY")
	@mkdir -p generated_documents
	docker compose up -d
	@echo "✅ Running at http://localhost:5000"

# Stop containers
stop:
	@echo "🛑 Stopping containers..."
	docker compose down

# Development mode (local Python)
dev:
	@echo "🔧 Starting in development mode..."
	@test -f .env || (cp .env.example .env && echo "⚠️  Created .env — add your ANTHROPIC_API_KEY")
	@mkdir -p generated_documents
	@pip install -r requirements.txt -q
	FLASK_ENV=development DEBUG=true python main.py

# Run tests
test:
	@echo "🧪 Running tests..."
	pytest tests/ -v --tb=short

# Run tests with coverage
test-cov:
	@echo "🧪 Running tests with coverage..."
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

# Lint
lint:
	@echo "🔍 Running linters..."
	flake8 app/ tests/ --max-line-length=120 --ignore=E203,W503
	black --check .
	isort --check-only .

# Format code
format:
	@echo "✨ Formatting code..."
	black .
	isort .

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	docker compose down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf generated_documents/*.pdf
	rm -rf .coverage htmlcov/ .pytest_cache/

# View logs
logs:
	docker compose logs -f mortgage-agent

# Shell access
shell:
	docker compose exec mortgage-agent /bin/bash

# Check if API key is set
check-env:
	@test -n "$$ANTHROPIC_API_KEY" || (echo "❌ ANTHROPIC_API_KEY is not set" && exit 1)
	@echo "✅ Environment looks good"
