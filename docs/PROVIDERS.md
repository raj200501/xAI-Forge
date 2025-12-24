# Providers

xAI-Forge ships with a small set of providers that share the same event model.
Each provider implements `Provider.run(task, tools, context, emit)`.

## heuristic

- Built-in lightweight provider for offline use.
- Uses deterministic heuristics and tool calls to respond.
- Ideal for tests and CI.

## ollama

- Connects to a local Ollama instance.
- Use when running local models on your workstation.
- Requires the Ollama server to be running separately.

## openai_compat

- Compatible with OpenAI-compatible APIs (self-hosted or hosted).
- Honors `OPENAI_API_KEY` and `OPENAI_BASE_URL` env vars.
- Network access still requires `--allow-net`.

## Adding a Provider

1. Create a new module in `xaiforge/providers/`.
2. Implement the `Provider` interface.
3. Register it in `xaiforge.agent.runner.PROVIDERS`.
