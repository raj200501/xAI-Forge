from __future__ import annotations

import importlib
import importlib.util
import json as jsonlib
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any


class HTTPStatusError(Exception):
    def __init__(self, message: str, response: Response) -> None:
        super().__init__(message)
        self.response = response


@dataclass
class URL:
    value: str

    @property
    def path(self) -> str:
        if "://" in self.value:
            _, rest = self.value.split("://", 1)
            if "/" in rest:
                return "/" + rest.split("/", 1)[1]
            return "/"
        return self.value


@dataclass
class Request:
    method: str
    url: URL
    json: Any | None = None


class Response:
    def __init__(
        self, status_code: int, content: str | bytes | None = None, json: Any | None = None
    ) -> None:
        self.status_code = status_code
        self._content = content
        self._json = json

    @property
    def text(self) -> str:
        if isinstance(self._content, bytes):
            return self._content.decode("utf-8", errors="replace")
        if self._content is None and self._json is not None:
            return jsonlib.dumps(self._json)
        return self._content or ""

    def json(self) -> Any:
        if self._json is not None:
            return self._json
        if self._content is None:
            return None
        return jsonlib.loads(self.text)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise HTTPStatusError(f"HTTP {self.status_code}", self)

    def iter_text(self) -> Iterator[str]:
        yield self.text

    def __enter__(self) -> Response:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class MockTransport:
    def __init__(self, handler: Callable[[Request], Response]) -> None:
        self._handler = handler

    def handle_request(self, request: Request) -> Response:
        return self._handler(request)


class Client:
    def __init__(
        self, base_url: str = "", timeout: float = 5.0, transport: MockTransport | None = None
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport

    def close(self) -> None:
        return None

    def __enter__(self) -> Client:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def get(self, url: str) -> Response:
        request = Request(method="GET", url=URL(self._full_url(url)))
        if self._transport:
            return self._transport.handle_request(request)
        with urllib.request.urlopen(request.url.value, timeout=self._timeout) as response:
            content = response.read()
            return Response(status_code=response.status, content=content)

    def stream(self, method: str, url: str, json: Any | None = None) -> Response:
        request = Request(method=method, url=URL(self._full_url(url)), json=json)
        if self._transport:
            return self._transport.handle_request(request)
        data = json and jsonlib.dumps(json).encode("utf-8") if method.upper() != "GET" else None
        req = urllib.request.Request(request.url.value, data=data, method=method.upper())
        with urllib.request.urlopen(req, timeout=self._timeout) as response:
            content = response.read()
            return Response(status_code=response.status, content=content)

    def _full_url(self, url: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return url
        if self._base_url:
            return f"{self._base_url}{url}"
        return url


_HTTPX_SPEC = importlib.util.find_spec("httpx")
if _HTTPX_SPEC is not None:
    _httpx = importlib.import_module("httpx")
    Client = _httpx.Client
    MockTransport = _httpx.MockTransport
    Response = _httpx.Response
    Request = _httpx.Request
    HTTPStatusError = _httpx.HTTPStatusError
