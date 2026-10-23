"""Benchmark harness behavior tests using an isolated fake connection."""
import pytest

from analytics.benchmark_local import measure


class FakeConnection:
    def __init__(self, values):
        self.values = iter(values)

    def execute(self, query):
        return self

    def fetchall(self):
        return next(self.values)


def test_measure_runs_warmup_plus_repetitions():
    result = measure(FakeConnection([[("ok",)]] * 4), "SELECT 1", 3)
    assert result["repetitions"] == 3
    assert result["min_ms"] <= result["median_ms"] <= result["max_ms"]


def test_measure_rejects_nonrepeatable_results():
    with pytest.raises(RuntimeError, match="Nonrepeatable"):
        measure(FakeConnection([[("warmup",)], [("a",)], [("b",)]]), "SELECT 1", 2)


def test_measure_rejects_zero_repetitions():
    with pytest.raises(ValueError, match="positive"):
        measure(FakeConnection([]), "SELECT 1", 0)
