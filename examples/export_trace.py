from __future__ import annotations

from pathlib import Path

from xaiforge.exporters import export_latest


def main() -> None:
    output = export_latest("markdown", base_dir=Path(".xaiforge"))
    print(f"Exported latest trace to {output}")


if __name__ == "__main__":
    main()
