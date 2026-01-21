from __future__ import annotations

from pathlib import Path

from xaiforge.policy.cli import (
    example_policy_rules,
    load_policy_config,
    render_policy_summary,
    summarize_policy,
)


def test_policy_summary_render(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(
        """
        {
          "description": "demo",
          "rules": [
            {"name": "allow-calc", "action": "allow", "tool": "calc"},
            {"name": "deny-http", "action": "deny", "tool": "http_get"},
            {"name": "monitor-file", "action": "monitor", "tool": "file_read"}
          ]
        }
        """,
        encoding="utf-8",
    )
    config = load_policy_config(policy_path)
    summary = summarize_policy(config)
    rendered = render_policy_summary(summary)
    assert "Rules: 3" in rendered
    assert "allow: 1" in rendered
    assert "deny: 1" in rendered
    assert "monitor: 1" in rendered


def test_policy_examples() -> None:
    rules = example_policy_rules()
    assert rules[0].tool == "http_get"
