from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field


@dataclass
class Counter:
    name: str
    description: str = ""
    value: int = 0

    def inc(self, amount: int = 1) -> None:
        self.value += amount


@dataclass
class Gauge:
    name: str
    description: str = ""
    value: float = 0.0

    def set(self, value: float) -> None:
        self.value = value


@dataclass
class Timer:
    name: str
    description: str = ""
    samples: list[float] = field(default_factory=list)

    def observe(self, duration_s: float) -> None:
        self.samples.append(duration_s)

    def stats(self) -> dict[str, float]:
        if not self.samples:
            return {"count": 0, "min": 0.0, "max": 0.0, "avg": 0.0}
        return {
            "count": float(len(self.samples)),
            "min": min(self.samples),
            "max": max(self.samples),
            "avg": sum(self.samples) / len(self.samples),
        }


@dataclass(frozen=True)
class MetricSnapshot:
    counters: dict[str, int]
    gauges: dict[str, float]
    timers: dict[str, dict[str, float]]


class MetricsRegistry:
    def __init__(self) -> None:
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._timers: dict[str, Timer] = {}
        self._lock = threading.Lock()

    def counter(self, name: str, description: str = "") -> Counter:
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name=name, description=description)
            return self._counters[name]

    def gauge(self, name: str, description: str = "") -> Gauge:
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name=name, description=description)
            return self._gauges[name]

    def timer(self, name: str, description: str = "") -> TimerContext:
        with self._lock:
            if name not in self._timers:
                self._timers[name] = Timer(name=name, description=description)
            timer = self._timers[name]
        return TimerContext(timer)

    def snapshot(self) -> MetricSnapshot:
        with self._lock:
            counters = {name: counter.value for name, counter in self._counters.items()}
            gauges = {name: gauge.value for name, gauge in self._gauges.items()}
            timers = {name: timer.stats() for name, timer in self._timers.items()}
        return MetricSnapshot(counters=counters, gauges=gauges, timers=timers)

    def merge(self, other: MetricsRegistry) -> None:
        for name, counter in other._counters.items():
            self.counter(name, counter.description).inc(counter.value)
        for name, gauge in other._gauges.items():
            self.gauge(name, gauge.description).set(gauge.value)
        for name, timer in other._timers.items():
            context = self.timer(name, timer.description)
            for sample in timer.samples:
                context.observe(sample)


class TimerContext:
    def __init__(self, timer: Timer) -> None:
        self._timer = timer
        self._start: float | None = None

    def __enter__(self) -> TimerContext:
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

    def stop(self) -> float:
        if self._start is None:
            return 0.0
        duration = time.perf_counter() - self._start
        self.observe(duration)
        self._start = None
        return duration

    def observe(self, duration: float) -> None:
        self._timer.observe(duration)


class MetricScope:
    def __init__(self, registry: MetricsRegistry, prefix: str) -> None:
        self._registry = registry
        self._prefix = prefix

    def counter(self, name: str, description: str = "") -> Counter:
        return self._registry.counter(f"{self._prefix}.{name}", description)

    def gauge(self, name: str, description: str = "") -> Gauge:
        return self._registry.gauge(f"{self._prefix}.{name}", description)

    def timer(self, name: str, description: str = "") -> TimerContext:
        return self._registry.timer(f"{self._prefix}.{name}", description)


class MetricExporter:
    def export(self, snapshot: MetricSnapshot) -> None:
        raise NotImplementedError


class InMemoryExporter(MetricExporter):
    def __init__(self) -> None:
        self.snapshots: list[MetricSnapshot] = []

    def export(self, snapshot: MetricSnapshot) -> None:
        self.snapshots.append(snapshot)


class PeriodicReporter:
    def __init__(self, registry: MetricsRegistry, exporters: Iterable[MetricExporter]) -> None:
        self._registry = registry
        self._exporters = list(exporters)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, interval_s: float = 5.0) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, args=(interval_s,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run(self, interval_s: float) -> None:
        while not self._stop_event.is_set():
            snapshot = self._registry.snapshot()
            for exporter in self._exporters:
                exporter.export(snapshot)
            self._stop_event.wait(interval_s)


class MetricReporter:
    def __init__(
        self, registry: MetricsRegistry, exporter_factory: Callable[[], MetricExporter]
    ) -> None:
        self._registry = registry
        self._exporter_factory = exporter_factory
        self._exporter: MetricExporter | None = None

    def flush(self) -> MetricSnapshot:
        snapshot = self._registry.snapshot()
        if self._exporter is None:
            self._exporter = self._exporter_factory()
        self._exporter.export(snapshot)
        return snapshot


class MetricSerializer:
    def to_dict(self, snapshot: MetricSnapshot) -> dict[str, dict[str, float] | dict[str, int]]:
        return {
            "counters": snapshot.counters,
            "gauges": snapshot.gauges,
            "timers": snapshot.timers,
        }

    def from_dict(self, payload: Mapping[str, dict[str, float] | dict[str, int]]) -> MetricSnapshot:
        return MetricSnapshot(
            counters={k: int(v) for k, v in payload.get("counters", {}).items()},
            gauges={k: float(v) for k, v in payload.get("gauges", {}).items()},
            timers={k: dict(v) for k, v in payload.get("timers", {}).items()},
        )
