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

.PHONY: setup fmt verify run demo doctor

setup:
	python -m pip install -e ".[dev]"
	cd web && npm install

fmt:
	ruff format .

verify:
	./scripts/verify.sh

run:
	python -m xaiforge serve

demo:
	./scripts/demo.sh

doctor:
	./scripts/doctor.sh
