.PHONY: dev test lint

dev:
	@echo "Starting API on http://127.0.0.1:8000"
	@echo "Starting web dev server on http://127.0.0.1:5173"
	@python -m xaiforge serve & \
	cd web && npm run dev

lint:
	ruff check .

test:
	pytest
	cd web && npm test && npm run build
