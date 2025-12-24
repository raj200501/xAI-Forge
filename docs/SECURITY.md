# Runtime Security Model

xAI-Forge is intentionally offline-first and ships with a minimal tool registry.
The runtime enforces a root sandbox and defaults to **no network access**.

## Root Sandboxing

- All file tools resolve paths relative to `--root`.
- Attempts to access paths outside the root raise errors.
- This keeps tool calls deterministic and local.

## `--allow-net` Flag

Network access is disabled unless explicitly enabled with `--allow-net` or the
UI toggle. This ensures runs are reproducible and do not exfiltrate data by
default.

## Threat Model

**In scope**
- Preventing accidental file reads outside the root.
- Ensuring network calls are opt-in.
- Verifying trace integrity via hashing.

**Out of scope**
- Malicious providers (use trusted providers only).
- Host-level isolation (use containers for stronger isolation).
- Protection against prompt injection (tools are still callable).

## Recommendations

- Run with a minimal root directory.
- Keep `--allow-net` disabled unless necessary.
- Use containers for untrusted tasks.
