from __future__ import annotations

import importlib
import importlib.util
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class _FieldInfo:
    default: Any = None
    default_factory: Callable[[], Any] | None = None


def Field(default: Any = None, default_factory: Callable[[], Any] | None = None) -> _FieldInfo:
    return _FieldInfo(default=default, default_factory=default_factory)


class BaseModel:
    def __init__(self, **data: Any) -> None:
        annotations = _collect_annotations(self.__class__)
        for name in annotations:
            if name in data:
                value = data[name]
            else:
                value = _resolve_default(getattr(self.__class__, name, None))
            setattr(self, name, value)

    def model_dump(self) -> dict[str, Any]:
        annotations = _collect_annotations(self.__class__)
        return {name: getattr(self, name) for name in annotations}

    def model_dump_json(self) -> str:
        return json.dumps(self.model_dump())

    @classmethod
    def model_validate(cls, payload: dict[str, Any]) -> BaseModel:
        return cls(**payload)


class TypeAdapter:
    def __init__(self, model: Any) -> None:
        self._model = model

    def json_schema(self) -> dict[str, Any]:
        return {"oneOf": []}

    def validate_python(self, payload: Any) -> Any:
        return payload


def _resolve_default(value: Any) -> Any:
    if isinstance(value, _FieldInfo):
        if value.default_factory is not None:
            return value.default_factory()
        return value.default
    return value


def _collect_annotations(model_cls: type) -> dict[str, Any]:
    annotations: dict[str, Any] = {}
    for base in reversed(model_cls.__mro__):
        annotations.update(getattr(base, "__annotations__", {}))
    return annotations


_PYDANTIC_SPEC = importlib.util.find_spec("pydantic")
if _PYDANTIC_SPEC is not None:
    _pydantic = importlib.import_module("pydantic")
    BaseModel = _pydantic.BaseModel
    Field = _pydantic.Field
    TypeAdapter = _pydantic.TypeAdapter
