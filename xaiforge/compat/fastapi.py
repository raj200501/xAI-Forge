from __future__ import annotations

import asyncio
import importlib
import importlib.util
import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from xaiforge.compat.sse_starlette import EventSourceResponse


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass
class _Route:
    method: str
    path: str
    endpoint: Callable[..., Any]


class FastAPI:
    def __init__(self, title: str | None = None) -> None:
        self.title = title or ""
        self._routes: list[_Route] = []

    def add_middleware(self, middleware_cls: Any, **kwargs: Any) -> None:
        _ = (middleware_cls, kwargs)

    def get(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._register("GET", path)

    def post(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._register("POST", path)

    def _register(
        self, method: str, path: str
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._routes.append(_Route(method=method, path=path, endpoint=func))
            func._path = path
            return func

        return decorator

    def _find_route(self, method: str, path: str) -> Callable[..., Any] | None:
        for route in self._routes:
            if route.method != method:
                continue
            if _match_path(route.path, path) is not None:
                return route.endpoint
        return None


class CORSMiddleware:
    def __init__(self, app: Any, **kwargs: Any) -> None:
        _ = (app, kwargs)


class Response:
    def __init__(self, status_code: int, payload: Any = None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


class TestClient:
    def __init__(self, app: FastAPI) -> None:
        self._app = app

    def get(self, path: str) -> Response:
        return self._request("GET", path)

    def post(self, path: str, json: Any | None = None) -> Response:
        return self._request("POST", path, json=json)

    def _request(self, method: str, path: str, json: Any | None = None) -> Response:
        endpoint = self._app._find_route(method, path)
        if not endpoint:
            return Response(404, {"detail": "Not Found"})
        try:
            result = _call_endpoint(endpoint, json, path)
        except HTTPException as exc:
            return Response(exc.status_code, {"detail": exc.detail})
        if isinstance(result, EventSourceResponse):
            return Response(200, {"event": "stream"})
        return Response(200, result)


def _call_endpoint(endpoint: Callable[..., Any], json_payload: Any | None, path: str) -> Any:
    params = _match_path(getattr(endpoint, "_path", path), path) or {}
    if json_payload is None:
        value = endpoint(**params)
    else:
        payload = _coerce_payload(endpoint, json_payload)
        value = endpoint(payload, **params) if params else endpoint(payload)
    if asyncio.iscoroutine(value):
        return asyncio.run(value)
    return value


def _coerce_payload(endpoint: Callable[..., Any], json_payload: Any) -> Any:
    signature = inspect.signature(endpoint)
    for param in signature.parameters.values():
        annotation = param.annotation
        if annotation is inspect._empty:
            continue
        if hasattr(annotation, "model_validate"):
            return annotation.model_validate(json_payload)
    return json_payload


def _match_path(route_path: str, actual_path: str) -> dict[str, str] | None:
    route_parts = route_path.strip("/").split("/")
    actual_parts = actual_path.strip("/").split("/")
    if len(route_parts) != len(actual_parts):
        return None
    params: dict[str, str] = {}
    for route_part, actual_part in zip(route_parts, actual_parts, strict=False):
        if route_part.startswith("{") and route_part.endswith("}"):
            key = route_part.strip("{}")
            params[key] = actual_part
        elif route_part != actual_part:
            return None
    return params


_FASTAPI_SPEC = importlib.util.find_spec("fastapi")
if _FASTAPI_SPEC is not None:
    _fastapi = importlib.import_module("fastapi")
    FastAPI = _fastapi.FastAPI
    HTTPException = _fastapi.HTTPException
    CORSMiddleware = importlib.import_module("fastapi.middleware.cors").CORSMiddleware
    TestClient = importlib.import_module("fastapi.testclient").TestClient
