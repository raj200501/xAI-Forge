from __future__ import annotations

import re
from typing import Any, Dict, List

from xaiforge.events import Message, Plan, ToolCall, ToolError, ToolResult
from xaiforge.providers.base import Provider
from xaiforge.tools.registry import ToolContext, ToolRegistry


class HeuristicProvider(Provider):
    name = "heuristic"

    async def run(
        self,
        task: str,
        tools: ToolRegistry,
        context: ToolContext,
        emit,
    ) -> str:
        plan_steps = [
            "Classify the task and pick tools",
            "Execute tool calls deterministically",
            "Verify outputs and craft final response",
        ]
        await emit(Plan(trace_id=context.trace_id, steps=plan_steps))
        task_lower = task.lower()
        tool_results: Dict[str, Any] = {}
        if re.search(r"\d+\s*[+\-*/^]\s*\d+", task_lower):
            expression = re.findall(r"[\d\s+\-*/^().]+", task)[0].strip()
            await emit(
                Message(
                    trace_id=context.trace_id,
                    role="assistant",
                    content=f"Planning to calculate: {expression}",
                )
            )
            tool_call = ToolCall(
                trace_id=context.trace_id,
                tool_name="calc",
                arguments={"expression": expression},
            )
            await emit(tool_call)
            try:
                result = tools.get("calc").handler(tool_call.arguments, context)
                tool_results["calc"] = result
                await emit(
                    ToolResult(
                        trace_id=context.trace_id,
                        tool_name="calc",
                        result={"expression": expression, "value": result},
                        parent_span_id=tool_call.span_id,
                    )
                )
            except Exception as exc:
                await emit(
                    ToolError(
                        trace_id=context.trace_id,
                        tool_name="calc",
                        error=str(exc),
                        parent_span_id=tool_call.span_id,
                    )
                )
        if "search" in task_lower or "grep" in task_lower or "repo" in task_lower:
            match = re.search(r"'([^']+)'|\"([^\"]+)\"", task)
            query = match.group(1) or match.group(2) if match else "TODO"
            await emit(
                Message(
                    trace_id=context.trace_id,
                    role="assistant",
                    content=f"Searching repository for '{query}'.",
                )
            )
            tool_call = ToolCall(
                trace_id=context.trace_id,
                tool_name="repo_grep",
                arguments={"query": query, "globs": ["**/*.py", "**/*.md"]},
            )
            await emit(tool_call)
            try:
                result = tools.get("repo_grep").handler(tool_call.arguments, context)
                tool_results["repo_grep"] = result
                await emit(
                    ToolResult(
                        trace_id=context.trace_id,
                        tool_name="repo_grep",
                        result=result,
                        parent_span_id=tool_call.span_id,
                    )
                )
            except Exception as exc:
                await emit(
                    ToolError(
                        trace_id=context.trace_id,
                        tool_name="repo_grep",
                        error=str(exc),
                        parent_span_id=tool_call.span_id,
                    )
                )
        final_lines: List[str] = ["Heuristic run complete."]
        if "calc" in tool_results:
            final_lines.append(
                f"Computed result: {tool_results['calc']} (via calc tool)."
            )
        if "repo_grep" in tool_results:
            matches = tool_results["repo_grep"]
            final_lines.append(f"Found {len(matches)} matches in repo.")
        if len(final_lines) == 1:
            final_lines.append("No specialized tool needed; responded directly.")
        final_answer = "\n".join(final_lines)
        await emit(
            Message(
                trace_id=context.trace_id,
                role="assistant",
                content=final_answer,
            )
        )
        return final_answer
