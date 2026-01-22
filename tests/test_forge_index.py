from __future__ import annotations

from pathlib import Path

import pytest

from xaiforge.agent.runner import run_task
from xaiforge.forge_index.builder import build_index, load_index_stats
from xaiforge.forge_index.query import fast_query


def test_index_build_and_query(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    import asyncio

    asyncio.run(run_task("2+2", "heuristic", tmp_path, False, []))
    stats = build_index(tmp_path / ".xaiforge")
    assert stats.trace_count >= 1
    results = fast_query(tmp_path / ".xaiforge", "type=message")
    assert results


def test_index_stats(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    stats = build_index(tmp_path / ".xaiforge")
    loaded = load_index_stats(tmp_path / ".xaiforge")
    assert loaded is not None
    assert loaded.trace_count == stats.trace_count
