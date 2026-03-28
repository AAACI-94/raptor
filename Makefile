.PHONY: dev test lint typecheck build up down logs clean

# Development
dev:
	cd backend && source .venv/bin/activate && uvicorn app.main:app --port 8000 --reload &
	cd frontend && npx vite --port 5177

# Testing
test:
	cd backend && source .venv/bin/activate && python -m pytest tests/ -v

test-quick:
	cd backend && source .venv/bin/activate && python -m pytest tests/ -q

# Quality
lint:
	cd backend && source .venv/bin/activate && python scripts/arch_lint.py

typecheck:
	cd frontend && npx tsc --noEmit

# Docker
build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=50

rebuild:
	docker compose down && docker compose up -d --build

# Cleanup
clean:
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -f backend/data/raptor.db
