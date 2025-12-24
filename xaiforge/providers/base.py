from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Awaitable, Callable

from xaiforge.events import Event
from xaiforge.tools.registry import ToolRegistry, ToolContext

EmitFunc = Callable[[Event], Awaitable[None]]


class Provider(ABC):
    name: str

    @abstractmethod
    async def run(
        self,
        task: str,
        tools: ToolRegistry,
        context: ToolContext,
        emit: EmitFunc,
    ) -> str:
        """Run the provider and emit events. Return final answer."""
        raise NotImplementedError
