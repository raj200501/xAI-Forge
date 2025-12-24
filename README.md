# xAI-Forge

Deterministic agent runtime + trace viewer with a Grok-coded vibe. Runs locally, no paid APIs required.

## Quickstart (60 seconds)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m xaiforge run --task "Solve 23*47 and show your steps"
```

## Demo commands

```bash
python -m xaiforge run --task "Search this repo for 'TODO' and summarize files" --root .
python -m xaiforge serve
python -m xaiforge replay <trace_id>
python -m xaiforge traces
python -m xaiforge doctor
python -m xaiforge bench
```

### Frontend

```bash
cd web
npm install
npm run dev
```

Open:
- API: http://localhost:8000
- UI: http://localhost:5173

## Screenshots

![trace list placeholder](docs/screenshots/traces.png)
![trace timeline placeholder](docs/screenshots/timeline.png)

## Architecture

```
+-----------------+       SSE       +----------------------+
| xaiforge CLI    | <-------------- | FastAPI /api/run     |
| (Typer + Rich)  |                 | /api/replay          |
+-----------------+                 +----------------------+
        |                                  |
        | JSONL traces                      | JSONL + manifest
        v                                  v
   .xaiforge/traces/               Vite React UI (5173)
```

## Security model

- File tools (`file_read`, `repo_grep`) are restricted to `--root`.
- Network access is disabled by default; `--allow-net` enables `http_get`.
- Trace data is stored locally under `.xaiforge/traces/`.

## Determinism & replay

- Each event is written as JSONL.
- A rolling SHA256 hash is computed (excluding the final `run_end` event).
- `manifest.json` stores the hash; `xaiforge replay` recomputes and verifies integrity.

## Providers

- **HeuristicProvider** (default): deterministic planner -> tool -> verifier -> answer.
- **OllamaProvider** (optional): uses local Ollama if available at `localhost:11434`.
- **OpenAICompatibleProvider** (optional): set `XAIFORGE_OPENAI_BASE_URL`, `XAIFORGE_OPENAI_API_KEY`.

## Troubleshooting

- Ensure Python 3.11+ and Node 18+ are installed.
- `python -m xaiforge doctor` checks basics.
- If ports 8000/5173 are busy, pass `--port` or update Vite config.

## CI

GitHub Actions runs:
- `pytest`
- `npm test` and `npm run build` in `web/`

## License

Apache-2.0
