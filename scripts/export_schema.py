from __future__ import annotations

import json
from pathlib import Path

from xaiforge.events import event_schema


def main() -> None:
    schema = event_schema()
    output_path = Path("docs") / "event_schema.json"
    output_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
