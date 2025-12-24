from pathlib import Path

import pytest

from xaiforge.tools.registry import ToolContext, build_registry


def test_file_read_restricted(tmp_path: Path) -> None:
    registry = build_registry()
    ctx = ToolContext(root=tmp_path)
    target = tmp_path / "note.txt"
    target.write_text("hello")
    result = registry.get("file_read").handler({"path": "note.txt"}, ctx)
    assert result == "hello"
    with pytest.raises(ValueError):
        registry.get("file_read").handler({"path": "/etc/passwd"}, ctx)


def test_calc() -> None:
    registry = build_registry()
    ctx = ToolContext(root=Path("."))
    result = registry.get("calc").handler({"expression": "2+3*4"}, ctx)
    assert result == "14"
