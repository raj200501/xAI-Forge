from __future__ import annotations

from pathlib import Path

from xaiforge.query import query_traces


def main() -> None:
    results = query_traces(Path(".xaiforge"), "type=tool_call")
    for trace_id, count in results.items():
        print(f"{trace_id}: {count} tool calls")


if __name__ == "__main__":
    main()
