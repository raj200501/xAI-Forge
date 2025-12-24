# Tool Registry

The tool registry lives in `xaiforge/tools/registry.py` and defines a curated
set of offline-friendly tools. Tools are described by a `ToolSpec` which includes
name, description, JSON schema parameters, and a Python handler.

## Built-in Tools

- `calc` – safe arithmetic evaluation.
- `regex_search` – regex matching over input strings.
- `file_read` – read files within the root directory.
- `repo_grep` – string search across files under the root.
- `http_get` – HTTP GET (requires `--allow-net`).

## JSON Schemas

Each tool exposes a JSON schema definition. These are surfaced in the API at
`/api/tools` to power UI tool tables.

## Adding a Tool

1. Define a handler that takes `(args, ctx)`.
2. Create a `ToolSpec` with a JSON schema in `build_registry()`.
3. Ensure the handler respects the root sandbox.

## Testing Tools

Add tests in `tests/test_tools.py` for any new tool or validation behavior.
