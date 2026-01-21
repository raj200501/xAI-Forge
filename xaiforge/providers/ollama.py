from __future__ import annotations

import json
from typing import Any

from xaiforge.compat import httpx
from xaiforge.events import Message, ToolCall, ToolError, ToolResult
from xaiforge.providers.base import Provider
from xaiforge.tools.registry import ToolContext, ToolRegistry


class OllamaProvider(Provider):
    name = "ollama"

    async def run(
        self,
        task: str,
        tools: ToolRegistry,
        context: ToolContext,
        emit,
    ) -> str:
        await emit(
            Message(
                trace_id=context.trace_id,
                role="system",
                content="Ollama provider expects JSON tool call responses.",
            )
        )
        payload = {
            "model": "llama3",
            "prompt": self._build_prompt(task, tools),
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post("http://localhost:11434/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            await emit(
                Message(
                    trace_id=context.trace_id,
                    role="assistant",
                    content=f"Ollama unavailable: {exc}",
                )
            )
            return "Ollama unavailable; fallback not configured."

        output = data.get("response", "")
        return await self._handle_model_output(output, tools, context, emit)

    def _build_prompt(self, task: str, tools: ToolRegistry) -> str:
        tool_desc = [
            {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.parameters,
            }
            for spec in tools.specs()
        ]
        return (
            "You are an agent. Respond with JSON lines of actions.\n"
            "Each line is either a tool_call {type, tool_name, arguments} or a message "
            "{type, content}.\n"
            f"Tools: {json.dumps(tool_desc)}\n"
            f"Task: {task}\n"
        )

    async def _handle_model_output(
        self,
        output: str,
        tools: ToolRegistry,
        context: ToolContext,
        emit,
    ) -> str:
        final_answer = ""
        for line in output.splitlines():
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("type") == "tool_call":
                tool_name = payload.get("tool_name")
                arguments: dict[str, Any] = payload.get("arguments", {})
                tool_call = ToolCall(
                    trace_id=context.trace_id,
                    tool_name=tool_name,
                    arguments=arguments,
                )
                await emit(tool_call)
                try:
                    result = tools.get(tool_name).handler(arguments, context)
                    await emit(
                        ToolResult(
                            trace_id=context.trace_id,
                            tool_name=tool_name,
                            result=result,
                            parent_span_id=tool_call.span_id,
                        )
                    )
                except Exception as exc:
                    await emit(
                        ToolError(
                            trace_id=context.trace_id,
                            tool_name=tool_name,
                            error=str(exc),
                            parent_span_id=tool_call.span_id,
                        )
                    )
            if payload.get("type") == "message":
                final_answer = payload.get("content", "")
                await emit(
                    Message(
                        trace_id=context.trace_id,
                        role="assistant",
                        content=final_answer,
                    )
                )
        return final_answer or "Ollama response processed."
