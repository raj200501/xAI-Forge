.PHONY: dev test lint

dev:
	python -m xaiforge serve

lint:
	ruff check .

test:
	pytest
	cd web && npm test && npm run build
