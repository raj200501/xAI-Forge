from __future__ import annotations

import ast
import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xaiforge.compat import httpx


@dataclass
class ToolContext:
    root: Path
    allow_net: bool = False
    trace_id: str = ""


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[dict[str, Any], ToolContext], Any]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def specs(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def get(self, name: str) -> ToolSpec:
        return self._tools[name]


class SafeEval(ast.NodeVisitor):
    allowed_nodes = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant)
    allowed_ops = (
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.Mod,
        ast.USub,
        ast.UAdd,
    )

    def visit(self, node: ast.AST) -> Any:
        if not isinstance(node, self.allowed_nodes + self.allowed_ops):
            raise ValueError(f"Disallowed expression: {type(node).__name__}")
        return super().visit(node)

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left**right
        if isinstance(node.op, ast.Mod):
            return left % right
        raise ValueError("Unsupported operator")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        value = self.visit(node.operand)
        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.UAdd):
            return +value
        raise ValueError("Unsupported unary operator")

    def visit_Constant(self, node: ast.Constant) -> Any:
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numeric constants allowed")


def tool_calc(args: dict[str, Any], _ctx: ToolContext) -> str:
    expression = str(args.get("expression", ""))
    tree = ast.parse(expression, mode="eval")
    evaluator = SafeEval()
    value = evaluator.visit(tree)
    if isinstance(value, float) and math.isfinite(value):
        return f"{value:.6g}"
    return str(value)


def tool_regex_search(args: dict[str, Any], _ctx: ToolContext) -> list[str]:
    pattern = str(args.get("pattern", ""))
    text = str(args.get("text", ""))
    return re.findall(pattern, text)


def _ensure_within_root(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    root_resolved = root.resolve()
    if root_resolved not in resolved.parents and resolved != root_resolved:
        raise ValueError("Path is outside allowed root")
    return resolved


def tool_file_read(args: dict[str, Any], ctx: ToolContext) -> str:
    path = Path(str(args.get("path", "")))
    max_bytes = int(args.get("max_bytes", 20000))
    target = _ensure_within_root(path if path.is_absolute() else ctx.root / path, ctx.root)
    with target.open("rb") as handle:
        data = handle.read(max_bytes)
    return data.decode("utf-8", errors="replace")


def tool_repo_grep(args: dict[str, Any], ctx: ToolContext) -> list[dict[str, Any]]:
    query = str(args.get("query", ""))
    globs = args.get("globs", ["**/*"])
    results: list[dict[str, Any]] = []
    for pattern in globs:
        for path in ctx.root.glob(pattern):
            if path.is_dir():
                continue
            try:
                target = _ensure_within_root(path, ctx.root)
            except ValueError:
                continue
            try:
                text = target.read_text(encoding="utf-8")
            except Exception:
                continue
            for idx, line in enumerate(text.splitlines(), start=1):
                if query in line:
                    results.append(
                        {"path": str(target.relative_to(ctx.root)), "line": idx, "text": line}
                    )
            if len(results) > 200:
                return results
    return results


def tool_http_get(args: dict[str, Any], ctx: ToolContext) -> str:
    if not ctx.allow_net:
        raise ValueError("Network access disabled (use --allow-net)")
    url = str(args.get("url", ""))
    timeout_s = float(args.get("timeout_s", 5.0))
    with httpx.Client(timeout=timeout_s) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="calc",
            description="Evaluate a math expression.",
            parameters={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
            handler=tool_calc,
        )
    )
    registry.register(
        ToolSpec(
            name="regex_search",
            description="Search for regex matches in text.",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "text": {"type": "string"},
                },
                "required": ["pattern", "text"],
            },
            handler=tool_regex_search,
        )
    )
    registry.register(
        ToolSpec(
            name="file_read",
            description="Read a file within the root directory.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "max_bytes": {"type": "integer", "default": 20000},
                },
                "required": ["path"],
            },
            handler=tool_file_read,
        )
    )
    registry.register(
        ToolSpec(
            name="repo_grep",
            description="Search files within the root for a query.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "globs": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["query"],
            },
            handler=tool_repo_grep,
        )
    )
    registry.register(
        ToolSpec(
            name="http_get",
            description="Fetch a URL over HTTP.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "timeout_s": {"type": "number", "default": 5.0},
                },
                "required": ["url"],
            },
            handler=tool_http_get,
        )
    )
    return registry
