.PHONY: install install-api install-web dev-api dev-web lint test test-api test-web build docker-up docker-down

install: install-api install-web

install-api:
	cd backend && python -m pip install -e ".[dev]"

install-web:
	cd frontend && npm ci

dev-api:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-web:
	cd frontend && npm run dev

test: test-api test-web

test-api:
	cd backend && python -m pytest

test-web:
	cd frontend && npm test

lint:
	cd backend && python -m ruff check .
	cd frontend && npm run typecheck

build:
	cd frontend && npm run build

docker-up:
	docker compose up --build

docker-down:
	docker compose down
