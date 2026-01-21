from __future__ import annotations

from pathlib import Path

from xaiforge.demo import run_demo


def test_demo_run_creates_outputs(tmp_path: Path, monkeypatch) -> None:
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(
        """
        {
          "default_action": "allow",
          "rules": [
            {"name": "deny-http", "action": "deny", "tool": "http_get"}
          ]
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setenv("XAIFORGE_POLICY_FILE", str(policy_path))
    result = run_demo(policy_path)
    assert result.export_path.exists()
    assert result.bench_path.exists()
    assert result.query_matches >= 1
    assert result.event_count > 0
