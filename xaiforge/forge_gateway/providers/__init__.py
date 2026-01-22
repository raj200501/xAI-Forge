import sys
import types

if "httpx" not in sys.modules:
    httpx_stub = types.ModuleType("httpx")

    class _MissingHTTPX:
        def __init__(self, *args, **kwargs) -> None:
            raise ModuleNotFoundError(
                "httpx is required for network providers. Install xaiforge with dependencies."
            )

        def __getattr__(self, name: str) -> "_MissingHTTPX":
            raise ModuleNotFoundError(
                "httpx is required for network providers. Install xaiforge with dependencies."
            )

    httpx_stub.AsyncClient = _MissingHTTPX  # type: ignore[attr-defined]
    httpx_stub.Response = _MissingHTTPX  # type: ignore[attr-defined]
    sys.modules["httpx"] = httpx_stub

from xaiforge.forge_gateway.providers.base import ModelProvider
from xaiforge.forge_gateway.providers.local_http import LocalHTTPProvider
from xaiforge.forge_gateway.providers.mock import MockProvider
from xaiforge.forge_gateway.providers.openai_compat import OpenAICompatibleProvider

__all__ = [
    "ModelProvider",
    "LocalHTTPProvider",
    "MockProvider",
    "OpenAICompatibleProvider",
]
