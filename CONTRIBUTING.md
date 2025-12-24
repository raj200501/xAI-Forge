# Contributing to xAI-Forge

Thanks for your interest in contributing! This project values small, high-signal
changes and excellent documentation.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

cd web
npm install
```

## Running Locally

```bash
python -m xaiforge serve
cd web && npm run dev
```

## Tests

```bash
make test
```

## Linting

```bash
make lint
```

## Adding Tools

- Implement handlers in `xaiforge/tools/registry.py`.
- Keep tools deterministic and scoped to the root.
- Add tests in `tests/test_tools.py`.

## Adding Providers

- Implement the `Provider` interface in `xaiforge/providers/`.
- Register it in `xaiforge.agent.runner.PROVIDERS`.
- Document behavior in `docs/PROVIDERS.md`.

## PR Checklist

- [ ] Tests pass (`make test`)
- [ ] Docs updated if behavior changes
- [ ] No breaking changes to CLI or API routes
