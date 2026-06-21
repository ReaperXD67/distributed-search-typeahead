.PHONY: up down logs test build dataset performance smoke

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f backend frontend

test:
	docker compose run --rm backend pytest -q
	cd frontend && npm test -- --run

build:
	cd frontend && npm run build

dataset:
	python backend/scripts/generate_dataset.py

performance:
	python backend/scripts/benchmark.py --base-url http://localhost:8000

smoke:
	docker compose exec -T backend python scripts/smoke_test.py
