from __future__ import annotations

from pathlib import Path

import pytest

from xaiforge.policy.engine import PolicyEngine
from xaiforge.policy.models import PolicyAction, PolicyConfig, PolicyRule
from xaiforge.tools.policy_registry import PolicyToolRegistry
from xaiforge.tools.registry import ToolContext, build_registry


def test_policy_registry_allows_tool() -> None:
    config = PolicyConfig(
        rules=[
            PolicyRule(
                name="allow-calc",
                action=PolicyAction.ALLOW,
                tool="calc",
                reason="ok",
            )
        ],
        default_action=PolicyAction.DENY,
    )
    engine = PolicyEngine(config)
    registry = PolicyToolRegistry(build_registry(), engine)
    spec = registry.get("calc")
    result = spec.handler({"expression": "2+2"}, ToolContext(root=Path(".")))
    assert result == "4"


def test_policy_registry_denies_tool() -> None:
    config = PolicyConfig(
        rules=[
            PolicyRule(
                name="deny-repo",
                action=PolicyAction.DENY,
                tool="repo_grep",
                reason="blocked",
            )
        ],
        default_action=PolicyAction.ALLOW,
    )
    engine = PolicyEngine(config)
    registry = PolicyToolRegistry(build_registry(), engine)
    spec = registry.get("repo_grep")
    with pytest.raises(ValueError, match="Policy denied tool"):
        spec.handler({"query": "xAI"}, ToolContext(root=Path(".")))


def test_policy_registry_specs_wrap_handlers() -> None:
    config = PolicyConfig(default_action=PolicyAction.ALLOW)
    engine = PolicyEngine(config)
    registry = PolicyToolRegistry(build_registry(), engine)
    specs = registry.specs()
    assert any(spec.name == "calc" for spec in specs)
