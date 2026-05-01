.PHONY: help install test lint docker-build docker-up docker-down clean

help:
	@echo "YASAFlaskified — make targets"
	@echo "  make install      Install Python deps locally"
	@echo "  make test         Run pytest"
	@echo "  make lint         Run ruff"
	@echo "  make docker-build Build the Docker image"
	@echo "  make docker-up    Start the full stack (compose up -d)"
	@echo "  make docker-down  Stop the stack"
	@echo "  make clean        Remove build / cache artefacts"

install:
	pip install -r requirements.txt
	pip install pytest ruff

test:
	pytest myproject/tests -v --tb=short

lint:
	ruff check myproject

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache
