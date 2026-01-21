from __future__ import annotations

import importlib
import importlib.util
import inspect
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class _Option:
    default: Any


@dataclass(frozen=True)
class _Argument:
    default: Any


def Option(default: Any, *args: Any, **kwargs: Any) -> Any:
    _ = (args, kwargs)
    return _Option(default)


def Argument(default: Any, *args: Any, **kwargs: Any) -> Any:
    _ = (args, kwargs)
    return _Argument(default)


class Typer:
    def __init__(self, add_completion: bool = False) -> None:
        _ = add_completion
        self._commands: dict[str, Callable[..., Any]] = {}

    def command(
        self, name: str | None = None
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            cmd_name = name or func.__name__.replace("_", "-")
            self._commands[cmd_name] = func
            return func

        return decorator

    def __call__(self) -> None:
        argv = sys.argv[1:]
        if not argv or argv[0] in {"-h", "--help"}:
            self._print_help()
            return
        cmd_name = argv[0]
        func = self._commands.get(cmd_name)
        if func is None:
            raise SystemExit(f"Unknown command: {cmd_name}")
        kwargs = _parse_kwargs(func, argv[1:])
        func(**kwargs)

    def _print_help(self) -> None:
        print("Available commands:")
        for name in sorted(self._commands):
            print(f"  {name}")


def _parse_kwargs(func: Callable[..., Any], argv: list[str]) -> dict[str, Any]:
    sig = inspect.signature(func)
    params = list(sig.parameters.values())
    values: dict[str, Any] = {}
    positional_params = [p for p in params if p.kind in {p.POSITIONAL_OR_KEYWORD}]
    pos_index = 0
    idx = 0
    while idx < len(argv):
        token = argv[idx]
        if token.startswith("--"):
            name = token[2:].replace("-", "_")
            param = sig.parameters.get(name)
            if param is None:
                raise SystemExit(f"Unknown option: {token}")
            if _is_bool_param(param):
                values[name] = True
                idx += 1
                continue
            if idx + 1 >= len(argv):
                raise SystemExit(f"Option requires value: {token}")
            values[name] = _coerce(argv[idx + 1], param.annotation)
            idx += 2
        else:
            if pos_index >= len(positional_params):
                raise SystemExit(f"Unexpected argument: {token}")
            param = positional_params[pos_index]
            values[param.name] = _coerce(token, param.annotation)
            pos_index += 1
            idx += 1
    for param in params:
        if param.name in values:
            continue
        default = param.default
        if isinstance(default, (_Option, _Argument)):
            values[param.name] = default.default
        elif default is not inspect._empty:
            values[param.name] = default
    for name, value in values.items():
        if value is Ellipsis:
            raise SystemExit(f"Missing required option: --{name.replace('_', '-')}")
    return values


def _is_bool_param(param: inspect.Parameter) -> bool:
    if param.annotation is bool:
        return True
    default = param.default
    return isinstance(default, _Option) and isinstance(default.default, bool)


def _coerce(value: str, annotation: Any) -> Any:
    if annotation is int:
        return int(value)
    if annotation is float:
        return float(value)
    if annotation is bool:
        return value.lower() in {"1", "true", "yes", "on"}
    return value


_TYPER_SPEC = importlib.util.find_spec("typer")
if _TYPER_SPEC is not None:
    _typer = importlib.import_module("typer")
    Typer = _typer.Typer
    Option = _typer.Option
    Argument = _typer.Argument
