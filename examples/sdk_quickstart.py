from __future__ import annotations

from xaiforge_sdk import Client


def main() -> None:
    client = Client()
    print("Available traces:")
    for trace in client.list_traces():
        print(f"- {trace.trace_id} ({trace.task})")

    print("\nStarting a run...")
    for event in client.start_run("Summarize the repository", allow_net=False):
        print(f"{event.type}: {event.ts}")
    client.close()


if __name__ == "__main__":
    main()
