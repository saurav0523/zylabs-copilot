.PHONY: help up down test test-backend test-frontend lint lint-backend lint-frontend migrate-db

help:
	@echo "Available commands:"
	@echo "  up             - Start the application with Docker Compose"
	@echo "  down           - Stop the application"
	@echo "  test           - Run tests for backend and frontend"
	@echo "  test-backend   - Run backend tests"
	@echo "  test-frontend  - Run frontend tests"
	@echo "  lint           - Lint backend and frontend"
	@echo "  lint-backend   - Lint backend (ruff + mypy)"
	@echo "  lint-frontend  - Lint frontend (eslint)"
	@echo "  migrate-db     - Run backend database migrations"

up:
	docker compose up --build

down:
	docker compose down

test: test-backend test-frontend

test-backend:
	cd backend && pytest --cov=. --cov-report=term-missing

test-frontend:
	cd frontend && npm run test

lint: lint-backend lint-frontend

lint-backend:
	cd backend && ruff check . && mypy --strict .

lint-frontend:
	cd frontend && npm run lint

migrate-db:
	cd backend && alembic upgrade head
