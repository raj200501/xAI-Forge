from __future__ import annotations

import json
import os
from typing import Any

from xaiforge.compat import httpx
from xaiforge.events import Message, ToolCall, ToolError, ToolResult
from xaiforge.providers.base import Provider
from xaiforge.tools.registry import ToolContext, ToolRegistry


class OpenAICompatibleProvider(Provider):
    name = "openai_compat"

    async def run(
        self,
        task: str,
        tools: ToolRegistry,
        context: ToolContext,
        emit,
    ) -> str:
        base_url = os.environ.get("XAIFORGE_OPENAI_BASE_URL")
        api_key = os.environ.get("XAIFORGE_OPENAI_API_KEY")
        model = os.environ.get("XAIFORGE_OPENAI_MODEL", "gpt-4o-mini")
        if not base_url or not api_key:
            await emit(
                Message(
                    trace_id=context.trace_id,
                    role="assistant",
                    content="OpenAI-compatible provider not configured.",
                )
            )
            return "OpenAI-compatible provider not configured."

        tool_payloads = [
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.parameters,
                },
            }
            for spec in tools.specs()
        ]
        messages = [{"role": "user", "content": task}]
        payload = {
            "model": model,
            "messages": messages,
            "tools": tool_payloads,
            "tool_choice": "auto",
        }
        headers = {"Authorization": f"Bearer {api_key}"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
            data = response.json()
        choices: list[dict[str, Any]] = data.get("choices", [])
        final_answer = ""
        for choice in choices:
            message = choice.get("message", {})
            if message.get("tool_calls"):
                for tool_call in message["tool_calls"]:
                    name = tool_call.get("function", {}).get("name")
                    arguments = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
                    event_call = ToolCall(
                        trace_id=context.trace_id,
                        tool_name=name,
                        arguments=arguments,
                    )
                    await emit(event_call)
                    try:
                        result = tools.get(name).handler(arguments, context)
                        await emit(
                            ToolResult(
                                trace_id=context.trace_id,
                                tool_name=name,
                                result=result,
                                parent_span_id=event_call.span_id,
                            )
                        )
                    except Exception as exc:
                        await emit(
                            ToolError(
                                trace_id=context.trace_id,
                                tool_name=name,
                                error=str(exc),
                                parent_span_id=event_call.span_id,
                            )
                        )
            if message.get("content"):
                final_answer = message["content"]
                await emit(
                    Message(
                        trace_id=context.trace_id,
                        role="assistant",
                        content=final_answer,
                    )
                )
        return final_answer or "OpenAI-compatible response processed."
