from __future__ import annotations

import json
from pathlib import Path

from xaiforge.compat import typer
from xaiforge.compat.rich import Console, Panel
from xaiforge.forge_index.builder import build_index, load_index_stats
from xaiforge.forge_index.query import fast_query

index_app = typer.Typer(add_completion=False)
console = Console()


@index_app.command("build")
def build_command() -> None:
    """Build the trace index."""
    stats = build_index(Path(".xaiforge"))
    console.print(Panel(json.dumps(stats.to_dict(), indent=2), title="Index build"))


@index_app.command("stats")
def stats_command() -> None:
    """Show index stats."""
    stats = load_index_stats(Path(".xaiforge"))
    if not stats:
        raise typer.BadParameter("Index not built")
    console.print(Panel(json.dumps(stats.to_dict(), indent=2), title="Index stats"))


@index_app.command("query")
def query_command(expr: str = typer.Argument(...)) -> None:
    """Run a fast query against the index."""
    results = fast_query(Path(".xaiforge"), expr)
    console.print(Panel(json.dumps(results, indent=2), title="Index query"))
