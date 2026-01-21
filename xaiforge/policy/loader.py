from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from xaiforge.policy.engine import PolicyEngine
from xaiforge.policy.models import PolicyAction, PolicyConfig, PolicyRule, RiskLevel


def load_policy_from_env() -> PolicyEngine | None:
    policy_file = os.getenv("XAIFORGE_POLICY_FILE")
    if not policy_file:
        return None
    path = Path(policy_file)
    if not path.exists():
        raise FileNotFoundError(f"Policy file not found: {policy_file}")
    engine = PolicyEngine.from_file(path)
    return engine


def default_policy() -> PolicyEngine:
    config = PolicyConfig(
        rules=[
            PolicyRule(
                name="block-network",
                action=PolicyAction.DENY,
                tool="http_get",
                risk=RiskLevel.HIGH,
                reason="Network access blocked by policy",
            )
        ],
        default_action=PolicyAction.ALLOW,
        default_risk=RiskLevel.LOW,
        description="Default policy denies network calls.",
    )
    return PolicyEngine(config)


def load_policy_payload(payload: dict[str, Any]) -> PolicyEngine:
    return PolicyEngine(PolicyConfig.from_dict(payload))


def load_policy_json(path: Path) -> PolicyEngine:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return load_policy_payload(payload)
