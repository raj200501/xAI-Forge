from __future__ import annotations

import importlib
import importlib.util
from dataclasses import dataclass, field
from typing import Any


class Console:
    def print(self, *args: Any, **kwargs: Any) -> None:
        _ = kwargs
        print(*args)

    def rule(self, title: str) -> None:
        print(f"--- {title} ---")


@dataclass
class Panel:
    renderable: str
    title: str | None = None

    def __str__(self) -> str:
        header = f"[{self.title}]\n" if self.title else ""
        return f"{header}{self.renderable}"


@dataclass
class Table:
    title: str | None = None
    columns: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)

    def add_column(self, name: str) -> None:
        self.columns.append(name)

    def add_row(self, *values: str) -> None:
        self.rows.append(list(values))

    def __str__(self) -> str:
        lines: list[str] = []
        if self.title:
            lines.append(self.title)
        if self.columns:
            lines.append(" | ".join(self.columns))
            lines.append(" | ".join(["---"] * len(self.columns)))
        for row in self.rows:
            lines.append(" | ".join(row))
        return "\n".join(lines)


_RICH_SPEC = importlib.util.find_spec("rich")
if _RICH_SPEC is not None:
    _rich_console = importlib.import_module("rich.console")
    _rich_panel = importlib.import_module("rich.panel")
    _rich_table = importlib.import_module("rich.table")
    Console = _rich_console.Console
    Panel = _rich_panel.Panel
    Table = _rich_table.Table
