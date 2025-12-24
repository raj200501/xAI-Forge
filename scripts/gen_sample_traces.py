from __future__ import annotations

import asyncio
from pathlib import Path

from xaiforge.agent.runner import run_task


async def main() -> None:
    tasks = [
        "Summarize the xAI-Forge repository",
        "Compute 23 * 47",
        "List all markdown files in the repo",
        "Explain the trace format in one sentence",
    ]
    for task in tasks:
        await run_task(task, "heuristic", Path("."), False, ["metrics_collector", "redactor"])


if __name__ == "__main__":
    asyncio.run(main())
