from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from xaiforge.policy.engine import PolicyEngine, PolicyViolation
from xaiforge.tools.registry import ToolContext, ToolRegistry, ToolSpec


@dataclass
class PolicyEvent:
    tool_name: str
    action: str
    allowed: bool
    reason: str
    risk: str


class PolicyToolRegistry(ToolRegistry):
    def __init__(self, base: ToolRegistry, policy: PolicyEngine) -> None:
        super().__init__()
        self._base = base
        self._policy = policy

    @property
    def policy(self) -> PolicyEngine:
        return self._policy

    def specs(self) -> list[ToolSpec]:
        return [self._wrap_spec(spec) for spec in self._base.specs()]

    def get(self, name: str) -> ToolSpec:
        spec = self._base.get(name)
        return self._wrap_spec(spec)

    def _wrap_spec(self, spec: ToolSpec) -> ToolSpec:
        def handler(args: dict[str, Any], ctx: ToolContext) -> Any:
            try:
                self._policy.enforce(spec.name, args)
            except PolicyViolation as exc:
                raise ValueError(
                    f"Policy denied tool '{spec.name}': {exc.decision.reason}"
                ) from exc
            return spec.handler(args, ctx)

        return ToolSpec(
            name=spec.name,
            description=spec.description,
            parameters=spec.parameters,
            handler=handler,
        )
