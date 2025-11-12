.PHONY: help setup test lint format typecheck clean dev

help:
	@echo "Canonizer - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup      Install dependencies and pre-commit hooks"
	@echo ""
	@echo "Development:"
	@echo "  make dev        Run API server in development mode"
	@echo "  make test       Run test suite with coverage"
	@echo "  make lint       Run ruff linter"
	@echo "  make format     Format code with ruff"
	@echo "  make typecheck  Run mypy type checker"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean      Remove cache and build artifacts"

setup:
	uv venv || python3 -m venv .venv
	. .venv/bin/activate && uv pip install -e ".[dev,connectors]"
	. .venv/bin/activate && pre-commit install

test:
	. .venv/bin/activate && pytest

lint:
	. .venv/bin/activate && ruff check .

format:
	. .venv/bin/activate && ruff format .

typecheck:
	. .venv/bin/activate && mypy canonizer/

dev:
	. .venv/bin/activate && uvicorn canonizer.api.server:app --reload --port 8000

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
