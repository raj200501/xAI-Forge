from __future__ import annotations

import json
from pathlib import Path

import pytest

from xaiforge.policy.engine import PolicyAuditor, PolicyEngine, PolicyReport, PolicyViolation
from xaiforge.policy.models import PolicyAction, PolicyConfig, PolicyDecision, PolicyRule, RiskLevel


def test_policy_rule_matches_tool_and_args() -> None:
    rule = PolicyRule(
        name="match-calc",
        action=PolicyAction.ALLOW,
        tool="calc",
        arg_patterns={"expression": "2+2"},
        risk=RiskLevel.LOW,
    )
    assert rule.matches("calc", {"expression": "2+2"})
    assert not rule.matches("calc", {"expression": "3+3"})
    assert not rule.matches("repo_grep", {"expression": "2+2"})


def test_policy_engine_default_allow() -> None:
    config = PolicyConfig(rules=[], default_action=PolicyAction.ALLOW)
    engine = PolicyEngine(config)
    decision = engine.evaluate("calc", {"expression": "1+1"})
    assert decision.allowed
    assert decision.action == PolicyAction.ALLOW
    assert decision.reason == "Default policy applied"


def test_policy_engine_denies_rule() -> None:
    config = PolicyConfig(
        rules=[
            PolicyRule(
                name="deny-network",
                action=PolicyAction.DENY,
                tool="http_get",
                risk=RiskLevel.HIGH,
                reason="No network",
            )
        ],
        default_action=PolicyAction.ALLOW,
    )
    engine = PolicyEngine(config)
    with pytest.raises(PolicyViolation) as exc:
        engine.enforce("http_get", {"url": "https://example.com"})
    assert exc.value.decision.action == PolicyAction.DENY
    assert exc.value.decision.risk == RiskLevel.HIGH


def test_policy_engine_monitor_allows() -> None:
    config = PolicyConfig(
        rules=[
            PolicyRule(
                name="monitor-file",
                action=PolicyAction.MONITOR,
                tool="file_read",
                risk=RiskLevel.MEDIUM,
                reason="Monitor file access",
            )
        ],
        default_action=PolicyAction.DENY,
    )
    engine = PolicyEngine(config)
    decision = engine.enforce("file_read", {"path": "demo.txt"})
    assert decision.allowed
    assert decision.action == PolicyAction.MONITOR


def test_policy_report_serialization(tmp_path: Path) -> None:
    report = PolicyReport(trace_id="trace-1")
    report.decisions.append(
        PolicyDecision(
            tool_name="calc",
            action=PolicyAction.ALLOW,
            allowed=True,
            risk=RiskLevel.LOW,
            reason="ok",
            matched_rules=("allow",),
        )
    )
    path = tmp_path / "policy.json"
    report.write_json(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["trace_id"] == "trace-1"
    assert payload["summary"]["allowed"] == 1


def test_policy_auditor_lists_high_risk() -> None:
    decisions = [
        PolicyDecision(
            tool_name="http_get",
            action=PolicyAction.DENY,
            allowed=False,
            risk=RiskLevel.HIGH,
            reason="blocked",
            matched_rules=("deny-network",),
        ),
        PolicyDecision(
            tool_name="calc",
            action=PolicyAction.ALLOW,
            allowed=True,
            risk=RiskLevel.LOW,
            reason="ok",
            matched_rules=("allow",),
        ),
    ]
    auditor = PolicyAuditor(decisions)
    high_risk = auditor.high_risk()
    assert len(high_risk) == 1
    assert high_risk[0].tool_name == "http_get"
